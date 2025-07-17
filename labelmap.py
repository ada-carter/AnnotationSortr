"""
Labelmap functionality for tinySort application.
Handles loading, saving, and editing friendly names for class folders.
"""

import json
import pathlib

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QScrollArea,
    QWidget, QFormLayout, QDialogButtonBox
)

from config import LABELMAP_FILE

# ─────────────────────────────────────────────────────────────
# LABELMAP
# ─────────────────────────────────────────────────────────────
def load_labelmap(base: pathlib.Path) -> dict[str, str]:
    f = base / LABELMAP_FILE
    if f.exists():
        try:
            with f.open('r', encoding='utf8') as fh:
                data = json.load(fh)
            # ensure string keys
            return {str(k): str(v) for k, v in data.items()}
        except Exception:
            pass
    return {}

def save_labelmap(base: pathlib.Path, mapping: dict[str, str]) -> None:
    f = base / LABELMAP_FILE
    try:
        with f.open('w', encoding='utf8') as fh:
            json.dump(mapping, fh, indent=2, sort_keys=True)
    except Exception:
        pass

class LabelmapDialog(QDialog):
    """Simple dialog to edit friendly names for class folders."""
    def __init__(self, base: pathlib.Path, classes: list[str], mapping: dict[str, str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Class Labelmap")
        self.setMinimumWidth(450)
        self.base = base
        self.classes = classes
        self.mapping = dict(mapping)  # copy
        
        # Set dialog styling
        self.setStyleSheet(
            "QDialog { background-color: #303030; color: #ffffff; }"
            "QLabel { color: #ffffff; }"
            "QLineEdit { background-color: #404040; color: #ffffff; border: 1px solid #555; "
            "border-radius: 4px; padding: 5px; }"
            "QPushButton { background-color: #2a82da; color: white; border-radius: 4px; "
            "padding: 6px 12px; min-width: 80px; }"
            "QPushButton:hover { background-color: #3a92ea; }"
            "QPushButton:pressed { background-color: #1a72ca; }"
        )
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Title
        title = QLabel("<h2>Edit Class Names</h2>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)
        
        # Description
        desc = QLabel("Set user-friendly names for each class folder:")
        main_layout.addWidget(desc)
        
        # Form in a scrollable area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        form_widget = QWidget()
        form = QFormLayout(form_widget)
        form.setSpacing(10)
        form.setContentsMargins(5, 5, 5, 5)
        
        self._edits: dict[str, QLineEdit] = {}
        for cls in classes:
            edit = QLineEdit(self.mapping.get(cls, ""))
            edit.setPlaceholderText(f"Friendly name for '{cls}'")
            form.addRow(f"<b>{cls}</b>:", edit)
            self._edits[cls] = edit
            
        scroll.setWidget(form_widget)
        main_layout.addWidget(scroll, 1)
        
        # Buttons
        bbox = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel
        )
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        main_layout.addWidget(bbox)

    def accept(self):
        self.mapping = {cls: e.text().strip() for cls, e in self._edits.items() if e.text().strip()}
        save_labelmap(self.base, self.mapping)
        super().accept()