"""
Utility functions for tinySort application.
Contains image handling, file scanning, and async loading utilities.
"""

import os
import pathlib
from functools import lru_cache

from PyQt6.QtCore import Qt, QRunnable, pyqtSignal, QObject
from PyQt6.QtGui import QPixmap, QPainter, QPixmapCache

from config import IMG_EXTS


def gather_images(directory: pathlib.Path, max_depth: int = 3, limit: int = None) -> list[pathlib.Path]:
    """
    Safely gather images from directory with memory protection.
    Args:
        directory: Path to scan
        max_depth: Maximum recursion depth to prevent deep directory scanning
        limit: Maximum number of images to return (None for no limit)
    """
    if not directory.exists():
        return []
    
    images = []
    try:
        # Use iterative approach instead of recursive glob to control memory usage
        def _scan_directory(path: pathlib.Path, current_depth: int = 0):
            if current_depth > max_depth:
                return
            
            try:
                # Use scandir for better performance and error handling
                with os.scandir(path) as entries:
                    for entry in entries:
                        if limit and len(images) >= limit:
                            return
                            
                        try:
                            entry_path = pathlib.Path(entry.path)
                            
                            if entry.is_file():
                                if entry_path.suffix.lower() in IMG_EXTS:
                                    images.append(entry_path)
                            elif entry.is_dir() and current_depth < max_depth:
                                # Skip hidden directories and common problematic paths
                                dir_name = entry.name.lower()
                                if not (dir_name.startswith('.') or 
                                       dir_name in {'temp', 'tmp', 'cache', 'appdata', 'localcache'}):
                                    _scan_directory(entry_path, current_depth + 1)
                        except (OSError, PermissionError, FileNotFoundError):
                            # Skip inaccessible files/directories
                            continue
            except (OSError, PermissionError, FileNotFoundError):
                # Skip inaccessible directories
                return
        
        _scan_directory(directory)
        
    except Exception:
        # Fallback: return empty list if any unexpected error occurs
        return []
    
    return images


@lru_cache(maxsize=4096)
def load_pixmap(path: pathlib.Path) -> QPixmap:
    """Safely load pixmap with error handling and caching."""
    key = str(path)
    pm = QPixmapCache.find(key)
    if pm is None:
        try:
            # Only attempt to load if file exists and is accessible
            if not path.exists():
                raise FileNotFoundError(f"File not found: {path}")
                
            pm = QPixmap(str(path))
            if pm.isNull():
                raise ValueError(f"Could not load image: {path}")
                
        except Exception:
            # Create fallback placeholder for any error
            pm = QPixmap(200, 200)
            pm.fill(Qt.GlobalColor.darkGray)
            try:
                painter = QPainter(pm)
                painter.setPen(Qt.GlobalColor.red)
                painter.drawText(pm.rect(), Qt.AlignmentFlag.AlignCenter, "ERROR")
                painter.end()
            except Exception:
                # If even drawing fails, just use the gray rectangle
                pass
                
        # Cache the result (whether successful or error placeholder)
        QPixmapCache.insert(key, pm)
    return pm


class ImageLoader(QRunnable):
    """Async image loader for background image loading."""
    
    class Sig(QObject):
        done = pyqtSignal(str, QPixmap)
        
    def __init__(self, path: pathlib.Path):
        super().__init__()
        self.path = path
        self.sig = ImageLoader.Sig()
        
    def run(self):
        self.sig.done.emit(str(self.path), load_pixmap(self.path))
