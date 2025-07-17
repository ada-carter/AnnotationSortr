"""
Project page functionality for tinySort application.
Per-project class selection screen with preview functionality.
"""

import pathlib

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QKeySequence, QSize
from PyQt6.QtGui import QIcon, QShortcut
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QLineEdit, QSizePolicy, QDialog
)

from config import BTN_STYLES, PANEL_STYLE, KEYS, PREVIEW_FPS, PREVIEW_CAP
from labelmap import load_labelmap, LabelmapDialog
from utils import gather_images, load_pixmap

# ─────────────────────────────────────────────────────────────
# PROJECT CLASS PAGE (was HomePage)
# ─────────────────────────────────────────────────────────────
class ProjectPage(QWidget):
    """Per-project class selection screen (previous HomePage)."""
    open_class = pyqtSignal(pathlib.Path, str)
    edit_labelmap = pyqtSignal()
    back_projects = pyqtSignal()

    def __init__(self, base: pathlib.Path):
        super().__init__()
        self.base: pathlib.Path = base
        self.labelmap: dict[str, str] = load_labelmap(self.base)
        self.preview_timer = QTimer(self)
        self.preview_timer.timeout.connect(self._next_preview)
        self.preview_paths: list[pathlib.Path] = []
        self.prev_index = 0

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Header bar with title and buttons
        header_bar = QWidget()
        header_bar.setStyleSheet(PANEL_STYLE)
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(15, 10, 15, 10)
        
        # Project title with styled text
        title = QLabel(f"<h1 style='margin:0;color:#ffffff;'>{self.base.name}</h1>")
        header_layout.addWidget(title)
        
        # Projects home button in header
        btn_proj_home = QPushButton("Projects ⌂")
        btn_proj_home.setStyleSheet(BTN_STYLES['home'])
        btn_proj_home.clicked.connect(self.back_projects.emit)
        header_layout.addWidget(btn_proj_home, 0, Qt.AlignmentFlag.AlignRight)
        
        main_layout.addWidget(header_bar)
        
        # Content area
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(15)
        
        # Left panel
        left_panel = QWidget()
        left_panel.setStyleSheet(PANEL_STYLE)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        
        # Project path label with better styling
        path_label = QLabel("<b>Project Path:</b>")
        path_label.setStyleSheet("color: #aaaaaa; margin-bottom: 5px;")
        left_layout.addWidget(path_label)
        
        self.lbl_proj = QLabel(str(self.base))
        self.lbl_proj.setStyleSheet("background-color: rgba(30,30,30,120); padding: 5px; border-radius: 4px;")
        self.lbl_proj.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self.lbl_proj.setWordWrap(True)
        left_layout.addWidget(self.lbl_proj)
        left_layout.addSpacing(10)

        # Filter/search with styled input
        search_label = QLabel("<b>Filter Classes:</b>")
        search_label.setStyleSheet("color: #aaaaaa;")
        left_layout.addWidget(search_label)
        
        self.search_box = QLineEdit()
        self.search_box.setStyleSheet(
            "QLineEdit { background: rgba(30,30,30,120); border: 1px solid #555; "
            "border-radius: 4px; padding: 5px; color: white; }"
        )
        self.search_box.setPlaceholderText("Type to filter...")
        self.search_box.textChanged.connect(self._filter_list)
        left_layout.addWidget(self.search_box)
        left_layout.addSpacing(10)

        # Class list with better styling
        classes_label = QLabel("<b>Available Classes:</b>")
        classes_label.setStyleSheet("color: #aaaaaa;")
        left_layout.addWidget(classes_label)
        
        self.list = QListWidget()
        self.list.setStyleSheet(
            "QListWidget { background: rgba(30,30,30,120); border: 1px solid #555; "
            "border-radius: 4px; padding: 5px; }"
            "QListWidget::item { padding: 5px; border-radius: 3px; }"
            "QListWidget::item:selected { background: rgba(45,137,239,150); }"
            "QListWidget::item:hover { background: rgba(60,60,60,150); }"
        )
        self.list.itemSelectionChanged.connect(self._selection_changed)
        self.list.itemDoubleClicked.connect(self._launch)
        left_layout.addWidget(self.list, 1)

        # Control buttons with modern styling
        btn_row = QHBoxLayout()
        
        self.open_btn = QPushButton("Open Selected Class")
        self.open_btn.setStyleSheet(BTN_STYLES['primary'])
        self.open_btn.clicked.connect(lambda: self._launch(self.list.currentItem()))
        self.open_btn.setEnabled(False)

        self.lblmap_btn = QPushButton("Edit Class Names")
        self.lblmap_btn.setStyleSheet(BTN_STYLES['info'])
        self.lblmap_btn.clicked.connect(self._edit_labelmap)
        
        btn_row.addWidget(self.open_btn)
        btn_row.addWidget(self.lblmap_btn)
        left_layout.addLayout(btn_row)

        # Preview area with modern styling
        right_panel = QWidget()
        right_panel.setStyleSheet(PANEL_STYLE)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        preview_label = QLabel("<h3>Class Preview</h3>")
        preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(preview_label)
        
        self.preview_lbl = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.preview_lbl.setStyleSheet("border:1px solid rgba(255,255,255,0.1); background:rgba(20,20,20,100); border-radius: 6px;")
        self.preview_lbl.setMinimumSize(QSize(400,400))
        self.preview_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_layout.addWidget(self.preview_lbl)
        
        # Add panels to content layout
        content_layout.addWidget(left_panel, 1)
        content_layout.addWidget(right_panel, 2)
        
        main_layout.addWidget(content, 1)

        # ESC to projects
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, activated=self.back_projects.emit)
        # H to projects also
        QShortcut(QKeySequence(KEYS['HOME']), self, activated=self.back_projects.emit)

        # populate immediately
        self._populate()

    # populate list with icons & counts
    def _populate(self):
        self.list.clear()
        self.open_btn.setEnabled(False)
        if not self.base:
            return

        def sort_key(p: pathlib.Path):
            return (0,int(p.name)) if p.name.isdigit() else (1,p.name.lower())

        classes: list[str] = []
        for d in sorted(self.base.iterdir(), key=sort_key):
            if d.is_dir() and d.name != 'delete':
                classes.append(d.name)

                # counts - use safe limited gathering
                kc = len(gather_images(d/'keep', max_depth=2)) if (d/'keep').exists() else 0
                rc = len(gather_images(d/'review', max_depth=2)) if (d/'review').exists() else 0
                dc = len(gather_images(self.base/'delete'/d.name, max_depth=2)) if (self.base/'delete'/d.name).exists() else 0

                text = d.name
                friendly = self.labelmap.get(d.name)
                if friendly:
                    text += f" — {friendly}"
                text += f"   [K:{kc} R:{rc} D:{dc}]"

                item = QListWidgetItem(text)
                item.setData(Qt.ItemDataRole.UserRole, d.name)  # store raw class name

                # Get icon safely with limits
                first_img = next(iter(gather_images(d, max_depth=2, limit=1)), None)
                if first_img:
                    try:
                        icon = QIcon(load_pixmap(first_img).scaled(
                            64,64,Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation))
                        item.setIcon(icon)
                    except Exception:
                        # Skip icon if loading fails
                        pass
                self.list.addItem(item)

        self._all_class_names = classes  # for labelmap editing

        # refresh filter
        self._filter_list(self.search_box.text())

    def _filter_list(self, text: str):
        text = text.strip().lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            raw_cls = item.data(Qt.ItemDataRole.UserRole)
            friendly = self.labelmap.get(raw_cls, "")
            item_text = (raw_cls + " " + friendly).lower()
            item.setHidden(bool(text) and text not in item_text)

    # selection change → start preview
    def _selection_changed(self):
        self.preview_timer.stop()
        self.preview_paths = []
        self.prev_index = 0
        sel = self.list.currentItem()
        self.open_btn.setEnabled(bool(sel))
        if not sel:
            self.preview_lbl.clear()
            return
        cls = sel.data(Qt.ItemDataRole.UserRole)
        folder = self.base / cls
        paths = gather_images(folder, max_depth=2, limit=PREVIEW_CAP * 2)  # Get more than needed for sampling
        if len(paths) > PREVIEW_CAP:
            # sample evenly
            step = max(1, len(paths)//PREVIEW_CAP)
            paths = paths[::step]
        self.preview_paths = paths
        if not self.preview_paths:
            self.preview_lbl.clear()
            return
        self.preview_timer.start(int(1000 / PREVIEW_FPS))
        self._show_preview()

    def _next_preview(self):
        if not self.preview_paths:
            return
        self.prev_index = (self.prev_index + 1) % len(self.preview_paths)
        self._show_preview()

    def _show_preview(self):
        p = self.preview_paths[self.prev_index]
        pm = load_pixmap(p)
        sz = self.preview_lbl.size()
        pm = pm.scaled(sz, Qt.AspectRatioMode.KeepAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
        self.preview_lbl.setPixmap(pm)

    def _launch(self, item: QListWidgetItem | None):
        if not item:
            return
        cls = item.data(Qt.ItemDataRole.UserRole)
        self.open_class.emit(self.base, cls)

    def _edit_labelmap(self):
        dlg = LabelmapDialog(self.base, self._all_class_names, self.labelmap, self)
        dlg.exec()
        if dlg.result() == QDialog.DialogCode.Accepted:
            self.labelmap = load_labelmap(self.base)
            self._populate()