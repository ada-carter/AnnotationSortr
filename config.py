"""
Configuration constants for tinySort application.
Contains UI settings, colors, styles, keybindings, and file extensions.
"""

import pathlib
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

# ─────────────────────────────────────────────────────────────
# SIZING & TIMING
# ─────────────────────────────────────────────────────────────
THUMB_SIZES   = [80, 120, 160]      # zoom preset heights (clickable)
GALLERY_THUMB = 160
SCALES        = [0.1, 0.25, 0.5, 0.75, 1.0, 1.25]
MAX_HISTORY   = 20                  # deeper undo
FPS           = 30
GLOW_MS       = 300                 
GLOW_OPACITY  = 80                  # 
PREVIEW_FPS   = 1                   # class-selection preview speed (frames / sec)
PREVIEW_CAP   = 100                 # max images sampled for preview rotation

# ─────────────────────────────────────────────────────────────
# FILES & PATHS
# ─────────────────────────────────────────────────────────────
LABELMAP_FILE = ".labelmap.json"    # stored in base directory
PROJECTS_FILE = pathlib.Path.home() / ".tinySort_projects.json"

# ─────────────────────────────────────────────────────────────
# COLORS
# ─────────────────────────────────────────────────────────────
# Modern UI colors
GLASS_BG = QColor(30, 30, 30, 180)
PANEL_BG = QColor(50, 50, 50, 220)
STATE_COL = {
    'keep':   QColor(50, 200, 50, GLOW_OPACITY),
    'review': QColor(50, 50, 200, GLOW_OPACITY),
    'delete': QColor(200, 50, 50, GLOW_OPACITY),
    'undo':   QColor(200, 200, 50, GLOW_OPACITY)
}

# ─────────────────────────────────────────────────────────────
# STYLES
# ─────────────────────────────────────────────────────────────
# Button styles
BTN_STYLES = {
    'default': "QPushButton { background-color: #505050; color: white; border-radius: 4px; padding: 6px 12px; }"
               "QPushButton:hover { background-color: #606060; }"
               "QPushButton:pressed { background-color: #404040; }",
    'primary': "QPushButton { background-color: #2a82da; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold; }"
               "QPushButton:hover { background-color: #3a92ea; }"
               "QPushButton:pressed { background-color: #1a72ca; }",
    'success': "QPushButton { background-color: #27ae60; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold; }"
               "QPushButton:hover { background-color: #2ebd6b; }"
               "QPushButton:pressed { background-color: #219555; }",
    'danger': "QPushButton { background-color: #e74c3c; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold; }"
              "QPushButton:hover { background-color: #f75c4c; }"
              "QPushButton:pressed { background-color: #d73c2c; }",
    'warning': "QPushButton { background-color: #f39c12; color: white; border-radius: 4px; padding: 6px 12px; font-weight: bold; }"
               "QPushButton:hover { background-color: #f4a922; }"
               "QPushButton:pressed { background-color: #e38c02; }",
    'info': "QPushButton { background-color: #3498db; color: white; border-radius: 4px; padding: 6px 12px; }"
            "QPushButton:hover { background-color: #44a8eb; }"
            "QPushButton:pressed { background-color: #2488cb; }",
    'home': "QPushButton { background-color: #8e44ad; color: white; border-radius: 4px; padding: 6px 12px; }"
            "QPushButton:hover { background-color: #9e54bd; }"
            "QPushButton:pressed { background-color: #7e349d; }"
}

# Reusable style for panels
PANEL_STYLE = "background-color: rgba(50, 50, 50, 220); border-radius: 8px; padding: 8px;"

# ─────────────────────────────────────────────────────────────
# KEYBINDINGS
# ─────────────────────────────────────────────────────────────
KEYS = {
    'KEEP' : Qt.Key.Key_J,
    'REV'  : Qt.Key.Key_R,
    'DEL'  : Qt.Key.Key_F,
    'UNDO' : Qt.Key.Key_U,
    'HOME' : Qt.Key.Key_H,      # now = Projects Home
    'QUIT' : Qt.Key.Key_Escape,
    'ZIN'  : Qt.Key.Key_X,
    'ZOUT' : Qt.Key.Key_Z,
    'PREV' : Qt.Key.Key_Left,
    'NEXT' : Qt.Key.Key_Right,
    'HELP' : Qt.Key.Key_Question
}

# ─────────────────────────────────────────────────────────────
# FILE EXTENSIONS
# ─────────────────────────────────────────────────────────────
IMG_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.gif'}
