"""
Gallery page functionality for tinySort application.
Provides overview and bulk editing of sorted images.
"""

import pathlib
import shutil

from PyQt6.QtCore import Qt, pyqtSignal, QKeySequence
from PyQt6.QtGui import QPixmap, QShortcut
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGridLayout,
    QScrollArea
)

from config import GALLERY_THUMB, STATE_COL, BTN_STYLES, PANEL_STYLE, KEYS
from utils import gather_images, load_pixmap

# ─────────────────────────────────────────────────────────────
# GALLERY PAGE
# ─────────────────────────────────────────────────────────────
class ThumbLabel(QLabel):
    toggled = pyqtSignal(object)  # emits self
    def __init__(self, path: pathlib.Path, state: str, thumb: QPixmap, parent=None):
        super().__init__(parent)
        self.path = path
        self.state = state
        self.setPixmap(thumb)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(GALLERY_THUMB)
        self.setFrameShape(QLabel.Shape.NoFrame)  # Changed from Box
        self._border()

    def _border(self):
        col = STATE_COL[self.state]
        # More modern rounded corners with box-shadow effect
        self.setStyleSheet(
            f"border-radius: 6px; padding: 4px; "
            f"background-color: rgba({col.red()},{col.green()},{col.blue()},40); "
            f"border: 2px solid rgba({col.red()},{col.green()},{col.blue()},180);"
        )

    def mouseDoubleClickEvent(self, _):
        self.toggled.emit(self)

class GalleryPage(QWidget):
    back_projects = pyqtSignal()
    back_project_home = pyqtSignal(pathlib.Path)  # to class list
    def __init__(self, base: pathlib.Path, cls: str, labelmap: dict[str, str], parent=None):
        super().__init__(parent)
        self.base = base
        self.cls = cls
        self.friendly = labelmap.get(cls, cls)
        self.class_dir = base / cls
        self.delete_dir = base / "delete" / cls
        self.entries: list[tuple[pathlib.Path, str]] = []
        for st, dir_ in (('keep', self.class_dir / 'keep'),
                         ('review', self.class_dir / 'review'),
                         ('delete', self.delete_dir)):
            if dir_.exists():
                for p in gather_images(dir_, max_depth=2):
                    self.entries.append((p, st))

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Header with title, counts and navigation
        header = QWidget()
        header.setStyleSheet(PANEL_STYLE)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(15, 10, 15, 10)
        
        # Title row with navigation buttons
        title_row = QHBoxLayout()
        
        kc, rc, dc = self._counts()
        title_html = (
            f"<h2 style='margin:0;color:#ffffff;'>Gallery — {self.cls}"
            f" <span style='font-size:60%;color:#aaaaaa;'>({self.friendly})</span></h2>"
        )
        title_label = QLabel(title_html)
        title_row.addWidget(title_label)
        title_row.addStretch(1)
        
        # Navigation buttons in header
        btn_project = QPushButton("Back to Classes")
        btn_project.setStyleSheet(BTN_STYLES['default'])
        btn_project.clicked.connect(lambda:self.back_project_home.emit(self.base))
        
        btn_home_projects = QPushButton("Projects ⌂")
        btn_home_projects.setStyleSheet(BTN_STYLES['home'])
        btn_home_projects.clicked.connect(self.back_projects.emit)
        
        title_row.addWidget(btn_project)
        title_row.addWidget(btn_home_projects)
        header_layout.addLayout(title_row)
        
        # Stats row
        stats_row = QHBoxLayout()
        stats_html = (
            f"<div style='font-size:14px;'>"
            f"<span style='color:#27ae60;font-weight:bold;'>Keep: {kc}</span> | "
            f"<span style='color:#3498db;font-weight:bold;'>Review: {rc}</span> | "
            f"<span style='color:#e74c3c;font-weight:bold;'>Delete: {dc}</span> | "
            f"<b>Total: {kc+rc+dc}</b>"
            f"</div>"
        )
        stats_label = QLabel(stats_html)
        stats_row.addWidget(stats_label)
        header_layout.addLayout(stats_row)
        
        main_layout.addWidget(header)
        
        # Gallery grid in scrollable area
        gallery_container = QWidget()
        gallery_container.setStyleSheet(PANEL_STYLE)
        
        grid_cont = QWidget()
        grid = QGridLayout(grid_cont)
        grid.setSpacing(15)
        grid.setContentsMargins(15, 15, 15, 15)
        cols = 6
        for i, (p, st) in enumerate(self.entries):
            thumb = load_pixmap(p).scaledToHeight(
                GALLERY_THUMB, Qt.TransformationMode.SmoothTransformation
            )
            lbl = ThumbLabel(p, st, thumb)
            lbl.toggled.connect(self._toggle)
            r, c = divmod(i, cols)
            grid.addWidget(lbl, r, c)

        scr = QScrollArea()
        scr.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scr.setWidgetResizable(True)
        scr.setWidget(grid_cont)
        
        gallery_layout = QVBoxLayout(gallery_container)
        gallery_layout.addWidget(scr)
        
        main_layout.addWidget(gallery_container, 1)

        # ESC to class list
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self,
                  activated=lambda:self.back_project_home.emit(self.base))

        # H = projects
        QShortcut(QKeySequence(KEYS['HOME']), self, activated=self.back_projects.emit)

    def _counts(self) -> tuple[int, int, int]:
        # Use limited depth and safe gathering for counts
        kc = len(gather_images(self.class_dir/'keep', max_depth=2)) if (self.class_dir/'keep').exists() else 0
        rc = len(gather_images(self.class_dir/'review', max_depth=2)) if (self.class_dir/'review').exists() else 0
        dc = len(gather_images(self.delete_dir, max_depth=2)) if self.delete_dir.exists() else 0
        return kc, rc, dc

    def _toggle(self, lbl: ThumbLabel):
        nxt = {'keep':'review','review':'delete','delete':'keep'}[lbl.state]
        dst_dir = (self.class_dir/nxt) if nxt!='delete' else self.delete_dir
        dst_dir.mkdir(parents=True,exist_ok=True)
        new_path = dst_dir/lbl.path.name
        shutil.move(lbl.path,new_path)
        ann_old = lbl.path.with_suffix('.txt')
        if ann_old.exists():
            shutil.move(ann_old,dst_dir/ann_old.name)
        lbl.path = new_path
        lbl.state = nxt
        lbl._border()