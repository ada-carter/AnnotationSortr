"""
Sorter page functionality for tinySort application.
Main image sorting interface with keyboard shortcuts and visual feedback.
"""

import pathlib
import shutil
import time
from collections import deque
from dataclasses import dataclass

from PyQt6.QtCore import Qt, QTimer, QThreadPool, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QShortcut, QKeySequence
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QProgressBar,
    QMessageBox, QSizePolicy, QToolButton, QFrame
)

from config import (
    THUMB_SIZES, SCALES, MAX_HISTORY, FPS, GLOW_MS, GLOW_OPACITY, 
    GLASS_BG, STATE_COL, BTN_STYLES, PANEL_STYLE, KEYS, IMG_EXTS
)
from utils import gather_images, load_pixmap, ImageLoader

# ─────────────────────────────────────────────────────────────
# SORTER PAGE
# ─────────────────────────────────────────────────────────────
@dataclass
class HistoryEntry:
    src: pathlib.Path           # destination path after move
    orig_parent: pathlib.Path   # original parent directory (class root OR delete)
    state: str                  # 'keep'|'review'|'delete'

class ClickableLabel(QLabel):
    clicked = pyqtSignal(int)
    def __init__(self, idx:int, parent=None):
        super().__init__(parent)
        self.idx = idx
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setStyleSheet(
            "border:1px solid rgba(255,255,255,0.2); border-radius: 4px; "
            "background-color: rgba(40,40,40,120); margin: 2px;"
        )
        
    def enterEvent(self, event):
        self.setStyleSheet(
            "border:1px solid rgba(52,152,219,0.8); border-radius: 4px; "
            "background-color: rgba(52,152,219,60); margin: 2px;"
        )
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.setStyleSheet(
            "border:1px solid rgba(255,255,255,0.2); border-radius: 4px; "
            "background-color: rgba(40,40,40,120); margin: 2px;"
        )
        super().leaveEvent(event)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.idx)
        super().mousePressEvent(event)

class ZoomGraphicsView(QGraphicsView):
    """GraphicsView that emits scaleChanged on Ctrl+wheel zoom."""
    scaleChanged = pyqtSignal(float)  # new scale factor from SCALES list approx
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_scale = 1.0
    def wheelEvent(self, e):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = e.angleDelta().y()
            factor = 1.1 if delta>0 else 1/1.1
            self._current_scale *= factor
            # clamp for sanity
            self._current_scale = max(min(self._current_scale, 5.0), 0.05)
            self.scaleChanged.emit(self._current_scale)
            e.accept()
        else:
            super().wheelEvent(e)

class SorterPage(QWidget):
    request_gallery = pyqtSignal(pathlib.Path, str)
    back_project_home = pyqtSignal(pathlib.Path)
    back_projects = pyqtSignal()
    def __init__(self, base: pathlib.Path, cls: str, labelmap: dict[str, str], parent=None):
        super().__init__(parent)
        self.base = base
        self.cls = cls
        self.friendly = labelmap.get(cls, cls)
        self.class_dir = base/cls
        self.delete_dir = base/"delete"/cls
        self.pool = QThreadPool.globalInstance()
        self.images = deque(self._unprocessed())
        self.scale_ix = SCALES.index(1.0)
        self.history: deque[HistoryEntry] = deque(maxlen=MAX_HISTORY)
        self.start_ts = time.time()
        self.highlight=None
        self.highlight_ts=0
        
        # Main layout with top toolbar
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Top toolbar with title and action buttons
        top_toolbar = QWidget()
        top_toolbar.setStyleSheet(PANEL_STYLE)
        top_toolbar_layout = QHBoxLayout(top_toolbar)
        top_toolbar_layout.setContentsMargins(10, 5, 10, 5)
        
        # Title label
        self.lbl_title = QLabel(
            f"<h2 style='margin:0;'>{self.cls} <span style='font-size:60%;color:#ccc;'>({self.friendly})</span></h2>"
        )
        top_toolbar_layout.addWidget(self.lbl_title)
        top_toolbar_layout.addStretch(1)
        
        # Action buttons in top toolbar
        btn_keep = QPushButton("Keep (J)")
        btn_keep.setStyleSheet(BTN_STYLES['success'])
        btn_keep.clicked.connect(lambda: self._sort('keep'))
        
        btn_review = QPushButton("Review (R)")
        btn_review.setStyleSheet(BTN_STYLES['info'])
        btn_review.clicked.connect(lambda: self._sort('review'))
        
        btn_delete = QPushButton("Delete (F)")
        btn_delete.setStyleSheet(BTN_STYLES['danger'])
        btn_delete.clicked.connect(lambda: self._sort('delete'))
        
        btn_undo = QPushButton("Undo (U)")
        btn_undo.setStyleSheet(BTN_STYLES['warning'])
        btn_undo.clicked.connect(self._undo)
        
        top_toolbar_layout.addWidget(btn_keep)
        top_toolbar_layout.addWidget(btn_review)
        top_toolbar_layout.addWidget(btn_delete)
        top_toolbar_layout.addWidget(btn_undo)
        
        # Navigation buttons
        self.btn_gallery = QPushButton("Gallery")
        self.btn_gallery.setStyleSheet(BTN_STYLES['primary'])
        self.btn_gallery.clicked.connect(lambda:self.request_gallery.emit(self.base,self.cls))
        
        self.btn_project = QPushButton("Classes")
        self.btn_project.setStyleSheet(BTN_STYLES['default'])
        self.btn_project.clicked.connect(lambda:self.back_project_home.emit(self.base))
        
        self.btn_projects = QPushButton("Projects ⌂")
        self.btn_projects.setStyleSheet(BTN_STYLES['home'])
        self.btn_projects.clicked.connect(self.back_projects.emit)
        
        top_toolbar_layout.addWidget(self.btn_gallery)
        top_toolbar_layout.addWidget(self.btn_project)
        top_toolbar_layout.addWidget(self.btn_projects)
        
        # Help button
        self.help_btn = QToolButton()
        self.help_btn.setText("?")
        self.help_btn.setToolTip("Show keyboard shortcuts")
        self.help_btn.setStyleSheet("QToolButton { background: #3498db; color: white; border-radius: 12px; font-weight: bold; min-width: 24px; min-height: 24px; }")
        self.help_btn.clicked.connect(self._show_shortcuts)
        top_toolbar_layout.addWidget(self.help_btn)
        
        main_layout.addWidget(top_toolbar)

        # Main content area with thumbnails, view, and info panel
        content_area = QHBoxLayout()
        content_area.setContentsMargins(0, 0, 0, 0)
        content_area.setSpacing(10)

        # left strip thumbnails (clickable zoom presets)
        self.thumb_container = QWidget(self)
        self.thumb_container.setFixedWidth(max(THUMB_SIZES)+20)
        self.thumb_container.setStyleSheet(PANEL_STYLE)
        vthumb = QVBoxLayout(self.thumb_container)
        vthumb.setContentsMargins(5,5,5,5)
        vthumb.setSpacing(8)
        self.thumb_labels: list[QLabel] = []
        for i, h in enumerate(THUMB_SIZES):
            lbl = ClickableLabel(idx=i, parent=self)
            lbl.setFixedHeight(h)
            lbl.setSizePolicy(QSizePolicy.Policy.Expanding,QSizePolicy.Policy.Fixed)
            lbl.clicked.connect(lambda _, ix=i: self._thumb_clicked(ix))
            vthumb.addWidget(lbl)
            self.thumb_labels.append(lbl)
        vthumb.addStretch(1)

        # main graphics view
        self.scene=QGraphicsScene(self)
        self.view=ZoomGraphicsView(self.scene,self)  # custom for wheel zoom
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.view.setBackgroundBrush(GLASS_BG)
        self.pixitem=QGraphicsPixmapItem()
        self.scene.addItem(self.pixitem)
        self.view.scaleChanged.connect(self._scale_changed_from_view)

        # right panel with info
        panel=QWidget(self)
        panel.setFixedWidth(300)
        panel.setStyleSheet(PANEL_STYLE)
        
        self.lbl_cnt=QLabel()
        self.lbl_prog=QLabel()
        self.bar=QProgressBar()
        self.bar.setFixedHeight(14)
        self.bar.setStyleSheet(
            "QProgressBar { background: rgba(50, 50, 50, 120); border: none; border-radius: 7px; }"
            "QProgressBar::chunk { background-color: #27ae60; border-radius: 7px; }"
        )
        self.lbl_zoom=QLabel()
        self.lbl_spd=QLabel()
        self.lbl_eta=QLabel()

        vp=QVBoxLayout(panel)
        vp.setContentsMargins(10,10,10,10)
        vp.addWidget(self.lbl_cnt)
        vp.addWidget(self.lbl_prog)
        vp.addWidget(self.bar)
        vp.addWidget(self.lbl_zoom)
        vp.addWidget(self.lbl_spd)
        vp.addWidget(self.lbl_eta)
        vp.addStretch(1)

        # Add components to content area
        content_area.addWidget(self.thumb_container)
        content_area.addWidget(self.view,1)
        content_area.addWidget(panel)
        
        main_layout.addLayout(content_area, 1)

        # timer UI updates
        self.timer=QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(int(1000/FPS))

        # keybindings
        self._keys()

        # kick off first load
        self._load_async()

    def _unprocessed(self) -> list[pathlib.Path]:
        """
        Efficiently gather unprocessed images in manageable chunks for large datasets.
        Only loads a chunk (e.g., 2000) at a time, but can still provide stats for the whole class.
        """
        CHUNK_SIZE = 2000
        # Use a generator to avoid loading all paths into memory
        def image_gen():
            for p in self.class_dir.rglob('*'):
                if p.is_file() and p.suffix.lower() in IMG_EXTS:
                    rel = p.relative_to(self.class_dir)
                    if rel.parts and rel.parts[0] in ('keep','review'):
                        continue
                    yield p
        # Only take the first CHUNK_SIZE unprocessed images
        imgs = []
        for i, p in enumerate(image_gen()):
            if i >= CHUNK_SIZE:
                break
            imgs.append(p)
        imgs.sort(key=lambda p: max(load_pixmap(p).width(), load_pixmap(p).height()), reverse=True)
        return imgs

    def _current(self) -> pathlib.Path | None:
        return self.images[0] if self.images else None

    def _load_async(self):
        if not self._current():
            self._finish()
            return
        job=ImageLoader(self._current())
        job.sig.done.connect(self._loaded)
        self.pool.start(job)

    def _loaded(self,pstr,pm):
        if self._current() and str(self._current())==pstr:
            self.pm_full=pm
            self._thumbs()
            self._zoom()

    def _thumbs(self):
        if not hasattr(self, "pm_full"): return
        for h,l in zip(THUMB_SIZES,self.thumb_labels):
            l.setPixmap(self.pm_full.scaledToHeight(
                h,Qt.TransformationMode.SmoothTransformation))

    def _zoom(self):
        if not hasattr(self, "pm_full"): return
        h=int(self.view.viewport().height()*SCALES[self.scale_ix])
        pix=self.pm_full.scaledToHeight(
            h,Qt.TransformationMode.SmoothTransformation)
        self.pixitem.setPixmap(pix)
        r=pix.rect()
        self.pixitem.setOffset(-r.width()/2,-r.height()/2)
        self.scene.setSceneRect(self.pixitem.boundingRect())
        self.lbl_zoom.setText(f"Zoom {int(SCALES[self.scale_ix]*100)}%")

    def _scale_changed_from_view(self, scale_factor: float):
        # external zoom (Ctrl+wheel)
        closest = min(range(len(SCALES)), key=lambda i: abs(SCALES[i]-scale_factor))
        self.scale_ix = closest
        self._zoom()

    def _keys(self):
        def sc(k,f): QShortcut(QKeySequence(k),self,activated=f)
        sc(KEYS['QUIT'],QApplication.instance().quit)
        sc(KEYS['PREV'],lambda:self._nav(1))
        sc(KEYS['NEXT'],lambda:self._nav(-1))
        sc(KEYS['ZIN'],lambda:self._z(1))
        sc(KEYS['ZOUT'],lambda:self._z(-1))
        sc(KEYS['KEEP'],lambda:self._sort('keep'))
        sc(KEYS['REV'],lambda:self._sort('review'))
        sc(KEYS['DEL'],lambda:self._sort('delete'))
        sc(KEYS['UNDO'],self._undo)
        sc(KEYS['HOME'],self.back_projects.emit)  # H=Projects
        sc(KEYS['HELP'],self._show_shortcuts)

    def _thumb_clicked(self, ix: int):
        """Clicking a thumb sets zoom preset ix."""
        if 0 <= ix < len(THUMB_SIZES):
            target_height = THUMB_SIZES[ix]
            vp_h = max(1, self.view.viewport().height())
            target_scale = target_height / vp_h
            closest = min(range(len(SCALES)), key=lambda i: abs(SCALES[i]-target_scale))
            self.scale_ix = closest
            self._zoom()

    def _nav(self,s:int):
            self.images.rotate(s)
            self._load_async()
        
    def _z(self,d:int):
            self.scale_ix=max(0,min(len(SCALES)-1,self.scale_ix+d))
            self._zoom()

    def _move(self,src:pathlib.Path,dst_dir:pathlib.Path) -> pathlib.Path:
        dst_dir.mkdir(parents=True,exist_ok=True)
        dst=dst_dir/src.name
        if dst == src:
            return dst
        shutil.move(src,dst)
        ann=src.with_suffix('.txt')
        if ann.exists():
            shutil.move(ann,dst_dir/ann.name)
        return dst

    def _sort(self,act:str):
        src=self._current()
        if src is None:
            return
        # Set highlight immediately for current image before moving to next
        self.highlight,self.highlight_ts=act,time.time()
        orig_parent = src.parent
        dst_dir=(self.class_dir/act) if act!='delete' else self.delete_dir
        new=self._move(src,dst_dir)
        self.history.append(HistoryEntry(src=new, orig_parent=orig_parent, state=act))
        self.images.popleft()
        self._load_async() 

    def _undo(self):
        if not self.history:
            return
        # Set highlight immediately before processing undo
        self.highlight,self.highlight_ts='undo',time.time()
        entry = self.history.pop()
        current_path = entry.src  # where it was moved
        # move back to original parent
        restored = self._move(current_path, entry.orig_parent)
        self.images.appendleft(restored)
        self._load_async()
        
    def _finish(self):
        msg=QMessageBox(self)
        msg.setWindowTitle("Class complete!")
        msg.setText(f"Class {self.cls} done.")
        gallery=msg.addButton("Open gallery",QMessageBox.ButtonRole.AcceptRole)
        proj=msg.addButton("Back to Classes",QMessageBox.ButtonRole.ActionRole)
        home=msg.addButton("Projects ⌂",QMessageBox.ButtonRole.RejectRole)
        msg.exec()
        if msg.clickedButton()==gallery:
            self.request_gallery.emit(self.base,self.cls)
        elif msg.clickedButton()==proj:
            self.back_project_home.emit(self.base)
        else:
            self.back_projects.emit()
            
    def _counts(self):
        # Efficiently count images in each state for large datasets - use safe gather_images
        def count_images(dir_path):
            if not dir_path.exists():
                return 0
            # Use our safe gather_images function instead of direct rglob
            return len(gather_images(dir_path, max_depth=3))
        kc = count_images(self.class_dir/'keep')
        rc = count_images(self.class_dir/'review')
        dc = count_images(self.delete_dir)
        return kc, rc, dc
        
    def _tick(self):
        # background glow - more subtle effect with border glow instead of full background
        if self.highlight and (time.time()-self.highlight_ts)*1000>GLOW_MS:
            self.highlight=None
            self.view.setBackgroundBrush(GLASS_BG)
            self.view.setStyleSheet("")
        elif self.highlight:
            # Keep original dark background but add a glowing border
            self.view.setBackgroundBrush(GLASS_BG)
            col = STATE_COL[self.highlight]
            # Create a subtle border glow effect
            self.view.setStyleSheet(
                f"border: 2px solid rgba({col.red()}, {col.green()}, {col.blue()}, {GLOW_OPACITY+40});"
                f"border-radius: 8px;"
            )

        # counts
        kc,rc,dc=self._counts()
        done=kc+rc+dc
        total=done+len(self.images)

        self.lbl_cnt.setText(f"<b>Keep {kc}</b> | Review {rc} | Delete {dc}")
        self.lbl_prog.setText(f"Processed {done}/{total}")
        self.bar.setRange(0,total)
        self.bar.setValue(done)

        if done:
            rate=done/(time.time()-self.start_ts)
            self.lbl_spd.setText(f"{int(rate*60)} img/min")
            eta=int((total-done)/rate) if rate else 0
            self.lbl_eta.setText(f"ETA {eta//60}:{eta%60:02d}")
        else:
            self.lbl_spd.clear()
            self.lbl_eta.clear()

    def _show_shortcuts(self):
        txt = (
            "<b>Keyboard Shortcuts</b><br><br>"
            "J = Keep<br>"
            "R = Review<br>"
            "F = Delete<br>"
            "U = Undo last<br>"
            "Left/Right = Prev/Next image<br>"
            "X / Z = Zoom in / out<br>"
            "Ctrl + Mouse Wheel = Zoom<br>"
            "H = Projects Home<br>"
            "Esc = Quit app (from Projects / global)<br>"
            "? = Show this help<br>"
        )
        QMessageBox.information(self, "Shortcuts", txt)
