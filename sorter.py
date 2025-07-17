# sorter.py
"""
tinySort
• keep / review / delete / undo / zoom
• async image loading & caching
• frosted-glass UI
• gallery re-assignment view
• user-friendly class-selection screen with live image preview
• persistent labelmap (friendly class names)
• clickable zoom thumbnails & mouse-wheel zoom
• shortcut legend overlay
• PROJECTS homescreen (multiple base directories)
"""

from __future__ import annotations

import sys, shutil, time, pathlib, itertools, json, typing as t, os
from dataclasses import dataclass
from collections import deque
from functools import lru_cache

from PyQt6.QtCore import (
    Qt, QTimer, QThreadPool, QRunnable, pyqtSignal, QObject, QSize, QPoint,
    QEvent
)
from PyQt6.QtGui import (
    QPixmap, QPainter, QColor, QKeySequence, QShortcut, QPixmapCache, QIcon,
    QAction, QWheelEvent, QPalette
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFileDialog, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QStackedWidget, QListWidget, QListWidgetItem,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QProgressBar,
    QScrollArea, QGridLayout, QMessageBox, QSizePolicy, QLineEdit, QDialog,
    QFormLayout, QDialogButtonBox, QFrame, QMenu, QToolButton, QSpacerItem,
    QStyle, QInputDialog
)

# Import configuration
from config import (
    THUMB_SIZES, GALLERY_THUMB, SCALES, MAX_HISTORY, FPS, GLOW_MS, GLOW_OPACITY,
    PREVIEW_FPS, PREVIEW_CAP, LABELMAP_FILE, PROJECTS_FILE, GLASS_BG, PANEL_BG,
    STATE_COL, BTN_STYLES, PANEL_STYLE, KEYS, IMG_EXTS
)

# Import utilities
from utils import gather_images, load_pixmap, ImageLoader

# Import modules
from projects import (
    ProjectListType, load_projects, save_projects, add_project, 
    remove_project, rename_project
)
from labelmap import load_labelmap, save_labelmap, LabelmapDialog
from gallery import GalleryPage
from sorterpage import SorterPage
from projectshome import ProjectsHome
from projectpage import ProjectPage
from auxwidgets import ClickableLabel, ZoomGraphicsView


# ─────────────────────────────────────────────────────────────
# MAIN WINDOW
# ─────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("tinySort")
        self.resize(1600, 950)
        
        # Set application-wide styling
        self.setStyleSheet(
            "QMainWindow { background-color: #252525; }"
            "QWidget { color: #ffffff; }"
            "QStackedWidget { background-color: #252525; }"
            "QLabel { color: #ffffff; }"
            "QPushButton { min-height: 28px; }"
        )
        
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # top-level projects home
        self.projects_home = ProjectsHome()
        self.projects_home.open_project.connect(self._open_project_page)
        self.stack.addWidget(self.projects_home)

        # status bar message
        self.statusBar().showMessage("Welcome to tinySort!")

    def _open_project_page(self, base: pathlib.Path):
        # find an existing ProjectPage for this base; else create
        for i in range(self.stack.count()):
            w = self.stack.widget(i)
            if isinstance(w, ProjectPage) and w.base == base:
                # refresh contents
                w.labelmap = load_labelmap(base)
                w._populate()
                self.stack.setCurrentWidget(w)
                return
        # not found: create new
        self._create_project_page(base)

    def _create_project_page(self, base: pathlib.Path):
        page = ProjectPage(base)
        page.back_projects.connect(self._back_projects)
        page.open_class.connect(self._open_sorter)
        self.stack.addWidget(page)
        self.stack.setCurrentWidget(page)

    def _open_sorter(self, base: pathlib.Path, cls: str):
        # refresh labelmap once per open
        labelmap = load_labelmap(base)
        sp = SorterPage(base, cls, labelmap)
        sp.back_project_home.connect(self._back_project_page)
        sp.back_projects.connect(self._back_projects)
        sp.request_gallery.connect(self._open_gallery)
        self.stack.addWidget(sp)
        self.stack.setCurrentWidget(sp)
        
    def _open_gallery(self, base: pathlib.Path, cls: str):
        labelmap = load_labelmap(base)
        gp = GalleryPage(base, cls, labelmap)
        gp.back_project_home.connect(self._back_project_page)
        gp.back_projects.connect(self._back_projects)
        self.stack.addWidget(gp)
        self.stack.setCurrentWidget(gp)
        
    def _back_project_page(self, base: pathlib.Path):
        # find an existing ProjectPage for this base; else create
        for i in range(self.stack.count()):
            w = self.stack.widget(i)
            if isinstance(w, ProjectPage) and w.base == base:
                # refresh contents
                w.labelmap = load_labelmap(base)
                w._populate()
                self.stack.setCurrentWidget(w)
                return
        # not found: create new
        self._create_project_page(base)

    def _back_projects(self):
        # show projects home
        self.projects_home.reload_projects()
        self.stack.setCurrentWidget(self.projects_home)
        # clean up other transient widgets
        for i in reversed(range(self.stack.count())):
            w = self.stack.widget(i)
            if w is self.projects_home:
                continue
            if isinstance(w, QWidget):
                self.stack.removeWidget(w)
                w.deleteLater()


# ─────────────────────────────────────────────────────────────
# ENTRY
# ─────────────────────────────────────────────────────────────
def main():
    if hasattr(Qt.ApplicationAttribute,'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling)
    if hasattr(Qt.ApplicationAttribute,'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

    # Set application style to Fusion for a modern look
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Create custom dark palette
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(45, 45, 45))
    dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(55, 55, 55))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(65, 65, 65))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
    app.setPalette(dark_palette)
    
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()