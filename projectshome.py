"""
Projects home page functionality for tinySort application.
Top-level screen for managing and selecting projects.
"""

import pathlib

from PyQt6.QtCore import Qt, pyqtSignal, QKeySequence, QSize
from PyQt6.QtGui import QIcon, QPixmap, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QInputDialog, QMessageBox, QMenu
)

from config import BTN_STYLES, PANEL_STYLE
from projects import ProjectListType, load_projects, add_project, remove_project, rename_project
from utils import gather_images, load_pixmap

# ─────────────────────────────────────────────────────────────
# PROJECTS HOME (top level)
# ─────────────────────────────────────────────────────────────
class ProjectsHome(QWidget):
    """Top-level screen listing all projects (base directories)."""
    open_project = pyqtSignal(pathlib.Path)  # path
    def __init__(self):
        super().__init__()

        self.projects: ProjectListType = []
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Header with title and logo
        header = QWidget()
        header.setStyleSheet(PANEL_STYLE)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(20, 20, 20, 20)
        
        # Title with modernized look
        title = QLabel("<h1 style='color:#ffffff;'>tinySort Projects</h1>", alignment=Qt.AlignmentFlag.AlignCenter)
        
        # Subtitle
        subtitle = QLabel("<p style='color:#aaaaaa;'>Select a project to organize or create a new one</p>", 
                         alignment=Qt.AlignmentFlag.AlignCenter)
        
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        main_layout.addWidget(header)
        
        # Projects container
        projects_container = QWidget()
        projects_container.setStyleSheet(PANEL_STYLE)
        projects_layout = QVBoxLayout(projects_container)
        projects_layout.setContentsMargins(15, 15, 15, 15)

        # List with better styling
        list_label = QLabel("<h3>Available Projects</h3>")
        projects_layout.addWidget(list_label)
        
        self.list = QListWidget()
        self.list.setStyleSheet(
            "QListWidget { background: rgba(30,30,30,120); border: 1px solid #555; "
            "border-radius: 4px; padding: 5px; }"
            "QListWidget::item { padding: 8px; border-radius: 4px; margin-bottom: 2px; }"
            "QListWidget::item:selected { background: rgba(45,137,239,150); }"
            "QListWidget::item:hover { background: rgba(60,60,60,150); }"
        )
        self.list.setIconSize(QSize(48, 48))
        self.list.itemDoubleClicked.connect(self._launch)
        self.list.itemSelectionChanged.connect(self._sel_changed)
        self.list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        projects_layout.addWidget(self.list)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.btn_open = QPushButton("Open Project")
        self.btn_open.setStyleSheet(BTN_STYLES['primary'])
        self.btn_open.setEnabled(False)
        self.btn_open.clicked.connect(lambda:self._launch(self.list.currentItem()))
        
        self.btn_add = QPushButton("Add New Project")
        self.btn_add.setStyleSheet(BTN_STYLES['success'])
        self.btn_add.clicked.connect(self._add_project)
        
        self.btn_rename = QPushButton("Rename")
        self.btn_rename.setStyleSheet(BTN_STYLES['info'])
        self.btn_rename.setEnabled(False)
        self.btn_rename.clicked.connect(self._rename_sel)
        
        self.btn_remove = QPushButton("Remove")
        self.btn_remove.setStyleSheet(BTN_STYLES['danger'])
        self.btn_remove.setEnabled(False)
        self.btn_remove.clicked.connect(self._remove_sel)
        
        button_layout.addWidget(self.btn_open)
        button_layout.addWidget(self.btn_add)
        button_layout.addWidget(self.btn_rename)
        button_layout.addWidget(self.btn_remove)
        
        projects_layout.addLayout(button_layout)
        main_layout.addWidget(projects_container, 1)
        
        # Footer with app info
        footer = QLabel("<div style='color:#777777; text-align:center; padding:10px;'>"
                       "tinySort!</div>")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(footer)

        # context menu
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._context)

        # ESC -> quit
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, activated=QApplication.instance().quit)

        self.reload_projects()

    # reload from disk
    def reload_projects(self):
        self.projects = load_projects()
        self.list.clear()
        for proj in self.projects:
            try:
                p = pathlib.Path(proj["path"])
                name = proj["name"] or p.name
                exists = p.exists()
                
                # counts if exists
                counts_txt = ""
                if exists:
                    try:
                        # Safely count directories, skip if permission error
                        n_cls = sum(1 for d in p.iterdir() if d.is_dir() and d.name != 'delete')
                        counts_txt = f"  ({n_cls} classes)"
                    except (OSError, PermissionError):
                        counts_txt = "  [ACCESS ERROR]"
                else:
                    counts_txt = "  [MISSING]"
                    
                item = QListWidgetItem(f"{name}{counts_txt}")
                item.setData(Qt.ItemDataRole.UserRole, proj)  # full dict
                
                if exists:
                    try:
                        # Safely get icon from first image, with limits to prevent memory issues
                        img = next(iter(gather_images(p, max_depth=2, limit=1)), None)
                        if img and img.exists():
                            try:
                                icon = QIcon(load_pixmap(img).scaled(
                                    64,64,Qt.AspectRatioMode.KeepAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation))
                                item.setIcon(icon)
                            except Exception:
                                # If icon loading fails, use default folder icon
                                pass
                    except Exception:
                        # If image gathering fails completely, skip icon
                        pass
                else:
                    # red-ish icon placeholder for missing projects
                    pm = QPixmap(32,32); pm.fill(Qt.GlobalColor.red)
                    item.setIcon(QIcon(pm))
                    
                self.list.addItem(item)
                
            except Exception as e:
                # If project is completely broken, add it with error indication
                try:
                    broken_name = proj.get("name", "Unknown") or "Unknown"
                    item = QListWidgetItem(f"{broken_name} [ERROR]")
                    item.setData(Qt.ItemDataRole.UserRole, proj)
                    pm = QPixmap(32,32); pm.fill(Qt.GlobalColor.red)
                    item.setIcon(QIcon(pm))
                    self.list.addItem(item)
                except Exception:
                    # Skip completely corrupted entries
                    continue
                    
        self._sel_changed()

    def _sel_changed(self):
        has = bool(self.list.currentItem())
        self.btn_open.setEnabled(has)
        self.btn_remove.setEnabled(has)
        self.btn_rename.setEnabled(has)

    def _launch(self, item: QListWidgetItem | None):
        if not item:
            return
        proj = item.data(Qt.ItemDataRole.UserRole)
        p = pathlib.Path(proj["path"])
        if not p.exists():
            QMessageBox.warning(self, "Missing path", f"Path does not exist:\n{p}")
            return
        self.open_project.emit(p)

    def _add_project(self):
        d = QFileDialog.getExistingDirectory(self, "Choose project directory")
        if not d:
            return
        p = pathlib.Path(d)
        name, ok = QInputDialog.getText(self, "Project Name",
                                        "Enter project name:",
                                        text=p.name)
        if not ok:
            return
        add_project(name.strip() or p.name, str(p))
        self.reload_projects()

    def _remove_sel(self):
        item = self.list.currentItem()
        if not item:
            return
        proj = item.data(Qt.ItemDataRole.UserRole)
        p = proj["path"]
        name = proj["name"] or pathlib.Path(p).name
        if QMessageBox.question(self, "Remove Project",
                                f"Remove '{name}' from list?\n(Files stay on disk.)") \
                == QMessageBox.StandardButton.Yes:
            remove_project(p)
            self.reload_projects()

    def _rename_sel(self):
        item = self.list.currentItem()
        if not item:
            return
        proj = item.data(Qt.ItemDataRole.UserRole)
        p = proj["path"]
        old = proj["name"] or pathlib.Path(p).name
        new, ok = QInputDialog.getText(self, "Rename Project",
                                       "New name:", text=old)
        if not ok:
            return
        rename_project(p, new.strip() or old)
        self.reload_projects()

    def _context(self, pos):
        item = self.list.itemAt(pos)
        if not item:
            return
        proj = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        act_open = menu.addAction("Open")
        act_rename = menu.addAction("Rename…")
        act_remove = menu.addAction("Remove")
        act = menu.exec(self.list.mapToGlobal(pos))
        if act == act_open:
            self._launch(item)
        elif act == act_rename:
            self._rename_sel()
        elif act == act_remove:
            self._remove_sel()
