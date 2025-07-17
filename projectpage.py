"""
Project page functionality for tinySort application.
Per-project class selection screen with preview functionality.
"""

import pathlib

from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QSize
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtGui import QIcon, QShortcut, QKeySequence
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget,
    QListWidgetItem, QLineEdit, QSizePolicy, QDialog
)

from config import BTN_STYLES, PANEL_STYLE, KEYS, PREVIEW_FPS, PREVIEW_CAP
import plotly.graph_objs as go
import plotly.io as pio
from plotly.subplots import make_subplots
from labelmap import load_labelmap, LabelmapDialog
from utils import gather_images, load_pixmap

# ─────────────────────────────────────────────────────────────
# PROJECT CLASS PAGE (was HomePage)
# ─────────────────────────────────────────────────────────────

class ProjectPage(QWidget):
    """Per-project class selection screen (previous HomePage)."""
    open_class = pyqtSignal(pathlib.Path, str)
    open_gallery = pyqtSignal(pathlib.Path, str)
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
        self.CHUNK_SIZE = 2000
        self.class_chunks: dict[str, list[list[pathlib.Path]]] = {}
        self.class_chunk_index: dict[str, int] = {}

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
        
        # Left panel (wider, larger icons)
        left_panel = QWidget()
        left_panel.setStyleSheet(PANEL_STYLE)
        left_panel.setMinimumWidth(340)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(14, 10, 14, 10)
        
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
        self.list.setIconSize(QSize(96, 96))
        self.list.setStyleSheet(
            "QListWidget { background: rgba(30,30,30,120); border: 1px solid #555; "
            "border-radius: 4px; padding: 8px; }"
            "QListWidget::item { padding: 10px; border-radius: 5px; }"
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

        self.gallery_btn = QPushButton("Gallery")
        self.gallery_btn.setStyleSheet(BTN_STYLES['info'])
        self.gallery_btn.clicked.connect(lambda: self._open_gallery(self.list.currentItem()))
        self.gallery_btn.setEnabled(False)

        self.lblmap_btn = QPushButton("Edit Class Names")
        self.lblmap_btn.setStyleSheet(BTN_STYLES['info'])
        self.lblmap_btn.clicked.connect(self._edit_labelmap)

        btn_row.addWidget(self.open_btn)
        btn_row.addWidget(self.gallery_btn)
        btn_row.addWidget(self.lblmap_btn)
        left_layout.addLayout(btn_row)


        # Right panel: consolidated preview and statistics
        right_panel = QWidget()
        right_panel.setStyleSheet(PANEL_STYLE)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)

        # Smaller preview slideshow
        preview_label = QLabel("<h3>Class Preview</h3>")
        preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(preview_label)

        self.preview_lbl = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.preview_lbl.setStyleSheet("border:1px solid rgba(255,255,255,0.1); background:rgba(20,20,20,100); border-radius: 6px;")
        self.preview_lbl.setMinimumSize(QSize(220,220))
        self.preview_lbl.setMaximumSize(QSize(220,220))
        self.preview_lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        right_layout.addWidget(self.preview_lbl, alignment=Qt.AlignmentFlag.AlignCenter)

        # Chunk info label and navigation (smaller) - wrapped in a QWidget for easy show/hide
        self.chunk_nav_widget = QWidget()
        chunk_nav_layout = QVBoxLayout(self.chunk_nav_widget)
        chunk_nav_layout.setContentsMargins(0, 0, 0, 0)
        chunk_nav_layout.setSpacing(0)
        self.chunk_info_lbl = QLabel("", alignment=Qt.AlignmentFlag.AlignCenter)
        self.chunk_info_lbl.setStyleSheet("color:#aaa;font-size:13px;margin-bottom:6px;")
        chunk_nav_layout.addWidget(self.chunk_info_lbl)
        chunk_nav_row = QHBoxLayout()
        self.btn_prev_chunk = QPushButton("Prev Chunk")
        self.btn_prev_chunk.setStyleSheet(BTN_STYLES['default'])
        self.btn_prev_chunk.clicked.connect(lambda: self._change_chunk(-1))
        self.btn_next_chunk = QPushButton("Next Chunk")
        self.btn_next_chunk.setStyleSheet(BTN_STYLES['default'])
        self.btn_next_chunk.clicked.connect(lambda: self._change_chunk(1))
        chunk_nav_row.addWidget(self.btn_prev_chunk)
        chunk_nav_row.addWidget(self.btn_next_chunk)
        chunk_nav_layout.addLayout(chunk_nav_row)
        right_layout.addWidget(self.chunk_nav_widget)
        # Plotly statistics graph
        self.stats_view = QWebEngineView()
        self.stats_view.setMinimumHeight(260)
        # Remove background and border for seamless dark theme
        self.stats_view.setStyleSheet("background: transparent; border: none;")
        try:
            self.stats_view.page().setBackgroundColor(Qt.GlobalColor.transparent)
        except Exception:
            pass
        right_layout.addWidget(self.stats_view, 1)

        # Add panels to content layout
        content_layout.addWidget(left_panel, 1)
        content_layout.addWidget(right_panel, 2)

        main_layout.addWidget(content, 1)

        # ESC to projects
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, activated=self.back_projects.emit)
        # H to projects also
        QShortcut(QKeySequence(KEYS['HOME']), self, activated=self.back_projects.emit)        # populate immediately
        self._populate()
        # Show dataset stats initially (before any class is selected)
        self._update_dataset_stats()

    # populate list with icons & counts
    def _populate(self):
        self.list.clear()
        self.open_btn.setEnabled(False)
        if not self.base:
            return

        def sort_key(p: pathlib.Path):
            return (0,int(p.name)) if p.name.isdigit() else (1,p.name.lower())

        classes: list[str] = []
        self.class_chunks.clear()
        self.class_chunk_index.clear()

        for d in sorted(self.base.iterdir(), key=sort_key):
            if d.is_dir() and d.name != 'delete':
                classes.append(d.name)

                # counts - use safe limited gathering
                kc = len(gather_images(d/'keep', max_depth=2)) if (d/'keep').exists() else 0
                rc = len(gather_images(d/'review', max_depth=2)) if (d/'review').exists() else 0
                # delete images are in base/delete/class
                dc = len(gather_images(self.base/'delete'/d.name, max_depth=2)) if (self.base/'delete'/d.name).exists() else 0

                # gather unsorted images (not in keep/review/delete)
                unsorted_imgs = []
                for p in d.rglob('*'):
                    if p.is_file() and p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.gif'}:
                        rel = p.relative_to(d)
                        if rel.parts and rel.parts[0] in ('keep','review'):
                            continue
                        unsorted_imgs.append(p)
                # chunk the unsorted images
                total_unsorted = len(unsorted_imgs)
                num_chunks = (total_unsorted + self.CHUNK_SIZE - 1) // self.CHUNK_SIZE if total_unsorted else 1
                chunks = [unsorted_imgs[i:i+self.CHUNK_SIZE] for i in range(0, total_unsorted, self.CHUNK_SIZE)]
                if not chunks:
                    chunks = [[]]
                self.class_chunks[d.name] = chunks
                self.class_chunk_index[d.name] = 0

                # total = all images in keep, review, delete, and unsorted
                total_imgs = kc + rc + dc + total_unsorted

                text = d.name
                friendly = self.labelmap.get(d.name)
                if friendly:
                    text += f" — {friendly}"
                text += f"   [K:{kc} R:{rc} D:{dc} | Total:{total_imgs} | Chunks:{num_chunks}]"

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
        self.gallery_btn.setEnabled(bool(sel))
        if not sel:
            self.chunk_nav_widget.hide()
            self.chunk_info_lbl.clear()
            # Show preview: loop through first image of each class
            self.preview_timer.stop()
            self.preview_paths = []
            self.prev_index = 0
            # Gather first image from each class
            preview_imgs = []
            for d in sorted(self.base.iterdir(), key=lambda p: (0,int(p.name)) if p.name.isdigit() else (1,p.name.lower())):
                if d.is_dir() and d.name != 'delete':
                    first_img = next(iter(gather_images(d, max_depth=2, limit=1)), None)
                    if first_img:
                        preview_imgs.append(first_img)
            self.preview_paths = preview_imgs
            if not self.preview_paths:
                self.preview_lbl.clear()
            else:
                self.preview_timer.start(int(1000 / PREVIEW_FPS))
                self._show_preview()
            # Show dataset-wide stats when no class is selected
            self._update_dataset_stats()
            return
        cls = sel.data(Qt.ItemDataRole.UserRole)
        chunks = self.class_chunks.get(cls, [[]])
        idx = self.class_chunk_index.get(cls, 0)
        num_chunks = len(chunks)
        # Only show chunk nav if there is more than 1 chunk and at least one image in the first chunk
        if (num_chunks > 1 and any(len(chunk) > 0 for chunk in chunks)) or (num_chunks == 1 and len(chunks[0]) > 0):
            self.chunk_nav_widget.show()
            self.chunk_info_lbl.setText(f"Chunk {idx+1} / {num_chunks} ({len(chunks[idx])} images)")
            self.btn_prev_chunk.setEnabled(idx > 0)
            self.btn_next_chunk.setEnabled(idx < num_chunks-1)
        else:
            self.chunk_nav_widget.hide()
            self.chunk_info_lbl.clear()
        # preview: show all images in all folders (keep, review, delete, unsorted)
        all_imgs = []
        d = self.base/cls
        for folder in [d/'keep', d/'review', self.base/'delete'/cls]:
            if folder.exists():
                all_imgs.extend(gather_images(folder, max_depth=2))
        # add unsorted
        for p in d.rglob('*'):
            if p.is_file() and p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.gif'}:
                rel = p.relative_to(d)
                if rel.parts and rel.parts[0] in ('keep','review'):
                    continue
                all_imgs.append(p)
        paths = all_imgs
        if len(paths) > PREVIEW_CAP:
            step = max(1, len(paths)//PREVIEW_CAP)
            paths = paths[::step]
        self.preview_paths = paths
        if not self.preview_paths:
            self.preview_lbl.clear()
        else:
            self.preview_timer.start(int(1000 / PREVIEW_FPS))
            self._show_preview()

        # Plotly stats for this class
        self._update_stats_plot(cls)

    def _update_stats_plot(self, cls: str):
        import math
        d = self.base/cls
        # Gather all images and stats
        folders = {
            'Keep': d/'keep',
            'Review': d/'review',
            'Delete': self.base/'delete'/cls
        }
        stats = {k: [] for k in folders}
        unsorted_imgs = []
        for p in d.rglob('*'):
            if p.is_file() and p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.gif'}:
                rel = p.relative_to(d)
                if rel.parts and rel.parts[0] in ('keep','review'):
                    continue
                unsorted_imgs.append(p)
        # Gather stats for each folder
        for k, folder in folders.items():
            if folder.exists():
                for p in gather_images(folder, max_depth=2):
                    stats[k].append(p)
        stats['Unsorted'] = unsorted_imgs

        # Compute summary stats
        def img_stats(paths):
            sizes = []
            ratios = []
            filesizes = []
            for p in paths:
                try:
                    pm = load_pixmap(p)
                    w, h = pm.width(), pm.height()
                    if w > 0 and h > 0:
                        sizes.append((w, h))
                        ratios.append(w/h)
                    filesizes.append(p.stat().st_size)
                except Exception:
                    continue
            n = len(paths)
            avg_w = int(sum(w for w, _ in sizes)/n) if n and sizes else 0
            avg_h = int(sum(h for _, h in sizes)/n) if n and sizes else 0
            avg_ratio = sum(ratios)/n if n and ratios else 0
            avg_filesize = int(sum(filesizes)/n) if n and filesizes else 0
            return n, avg_w, avg_h, avg_ratio, avg_filesize

        # Bar chart data (was pie)
        labels = list(stats.keys())
        values = [len(stats[k]) for k in labels]
        bar = go.Bar(
            x=labels,
            y=values,
            marker=dict(color=['#3a8dde', '#f7b731', '#eb3b5a', '#888']),
            text=values,
            textposition='auto',
            name='Count',
        )

        # Table of stats
        table_header = dict(values=["Folder", "Count", "Avg WxH", "Avg Aspect", "Avg Size (KB)"])
        table_cells = [[], [], [], [], []]
        for k in labels:
            n, avg_w, avg_h, avg_ratio, avg_filesize = img_stats(stats[k])
            table_cells[0].append(k)
            table_cells[1].append(str(n))
            table_cells[2].append(f"{avg_w}x{avg_h}" if avg_w and avg_h else "-")
            table_cells[3].append(f"{avg_ratio:.2f}" if avg_ratio else "-")
            table_cells[4].append(f"{avg_filesize//1024}" if avg_filesize else "-")
        table = go.Table(
            header=dict(
                values=table_header['values'],
                fill_color='#222',
                font=dict(color='white', size=12),
                align='center',
                line_color='#444',
                height=24
            ),
            cells=dict(
                values=table_cells,
                fill_color='#222',
                font=dict(color='white', size=11),
                align='center',
                line_color='#444',
                height=22
            )        )

        # Create subplots with bar chart on left, table on right
        fig = make_subplots(
            rows=1, cols=2,
            column_widths=[0.5, 0.5],
            specs=[[{"type": "bar"}, {"type": "table"}]],
            subplot_titles=[
                '<span style="margin-top:18px; display:block;">Distribution</span>',
                '<span style="margin-top:18px; display:block;">Statistics</span>'
            ]
        )

        fig.add_trace(bar, row=1, col=1)
        fig.add_trace(table, row=1, col=2)

        fig.update_layout(
            title_text="Class Image Stats",
            margin=dict(l=10, r=10, t=64, b=10),  # Increased top margin for more space
            height=260,
            paper_bgcolor='rgba(30,30,30,0)',
            plot_bgcolor='rgba(30,30,30,0)',
            font=dict(color='white', size=11),
            showlegend=False,
            xaxis=dict(title='Folder', tickfont=dict(color='white')),
            yaxis=dict(title='Count', tickfont=dict(color='white')),
        )
        
        # Render as HTML
        html = pio.to_html(fig, full_html=False, include_plotlyjs='cdn', config={"displayModeBar": False})
        # Inject CSS to remove all white backgrounds from plotly tables and figures
        custom_css = """
        <style>
        .plotly, .plotly * {
            background: transparent !important;
            background-color: transparent !important;
        }
        .plotly .table, .plotly .table * {
            background: transparent !important;
            background-color: transparent !important;
            color: #fff !important;
        }
        .plotly .table th, .plotly .table td {
            background: transparent !important;
            background-color: transparent !important;
        }
        </style>
        """
        html = html.replace('</head>', custom_css + '</head>')
        html = html.replace('<body>', '<body style="background-color:transparent; margin:0; padding:0;">')
        html = html.replace('class="plotly-graph-div"', 'class="plotly-graph-div" style="background-color:transparent;"')
        self.stats_view.setHtml(html)

    def _change_chunk(self, delta: int):
        sel = self.list.currentItem()
        if not sel:
            return
        cls = sel.data(Qt.ItemDataRole.UserRole)
        idx = self.class_chunk_index.get(cls, 0)
        chunks = self.class_chunks.get(cls, [[]])
        num_chunks = len(chunks)
        idx = max(0, min(num_chunks-1, idx+delta))
        self.class_chunk_index[cls] = idx
        self._selection_changed()

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

    def _open_gallery(self, item: QListWidgetItem | None):
        if not item:
            return
        cls = item.data(Qt.ItemDataRole.UserRole)
        self.open_gallery.emit(self.base, cls)

    def _edit_labelmap(self):
        dlg = LabelmapDialog(self.base, self._all_class_names, self.labelmap, self)
        dlg.exec()
        if dlg.result() == QDialog.DialogCode.Accepted:
            self.labelmap = load_labelmap(self.base)
            self._populate()

    def _update_dataset_stats(self):
        """Show dataset-wide statistics when no class is selected."""
        if not self.base:
            self.stats_view.setHtml("")
            return
            
        # Gather stats for all classes
        all_stats = {'Keep': 0, 'Review': 0, 'Delete': 0, 'Unsorted': 0}
        class_counts = []
        total_images = 0
        
        for d in self.base.iterdir():
            if d.is_dir() and d.name != 'delete':
                # Count images in each category for this class
                kc = len(gather_images(d/'keep', max_depth=2)) if (d/'keep').exists() else 0
                rc = len(gather_images(d/'review', max_depth=2)) if (d/'review').exists() else 0
                dc = len(gather_images(self.base/'delete'/d.name, max_depth=2)) if (self.base/'delete'/d.name).exists() else 0
                
                # Count unsorted
                unsorted_count = 0
                for p in d.rglob('*'):
                    if p.is_file() and p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff', '.gif'}:
                        rel = p.relative_to(d)
                        if rel.parts and rel.parts[0] in ('keep','review'):
                            continue
                        unsorted_count += 1
                
                all_stats['Keep'] += kc
                all_stats['Review'] += rc
                all_stats['Delete'] += dc
                all_stats['Unsorted'] += unsorted_count
                
                class_total = kc + rc + dc + unsorted_count
                class_counts.append((d.name, class_total))
                total_images += class_total
        
        # Sort classes by image count
        class_counts.sort(key=lambda x: x[1], reverse=True)
        
        # Bar chart for overall distribution (was pie)
        labels = list(all_stats.keys())
        values = [all_stats[k] for k in labels]
        bar = go.Bar(
            x=labels,
            y=values,
            marker=dict(color=['#3a8dde', '#f7b731', '#eb3b5a', '#888']),
            text=values,
            textposition='auto',
            name='Count',
        )
        
        # Create table showing class breakdown
        table_header = dict(values=["Class", "Total Images", "Keep", "Review", "Delete", "Unsorted"])
        table_cells = [[], [], [], [], [], []]
        
        # Add top 10 classes by image count
        for class_name, class_total in class_counts[:10]:
            d = self.base / class_name
            kc = len(gather_images(d/'keep', max_depth=2)) if (d/'keep').exists() else 0
            rc = len(gather_images(d/'review', max_depth=2)) if (d/'review').exists() else 0
            dc = len(gather_images(self.base/'delete'/class_name, max_depth=2)) if (self.base/'delete'/class_name).exists() else 0
            uc = class_total - kc - rc - dc
            
            table_cells[0].append(class_name[:15] + '...' if len(class_name) > 15 else class_name)
            table_cells[1].append(str(class_total))
            table_cells[2].append(str(kc))
            table_cells[3].append(str(rc))
            table_cells[4].append(str(dc))
            table_cells[5].append(str(uc))
        
        table = go.Table(
            header=dict(
                values=table_header['values'],
                fill_color='#333',
                font=dict(color='white', size=11),
                align='center',
                line_color='#555',
                height=22
            ),
            cells=dict(
                values=table_cells,
                fill_color='#222',
                font=dict(color='white', size=10),
                align='center',
                line_color='#444',
                height=20
            )
        )
        
        # Create subplots
        fig = make_subplots(
            rows=1, cols=2,
            column_widths=[0.4, 0.6],
            specs=[[{"type": "bar"}, {"type": "table"}]],
            subplot_titles=[
                '<span style="margin-top:18px; display:block;">Overall Distribution</span>',
                f'<span style="margin-top:18px; display:block;">Top Classes (Total: {total_images} images)</span>'
            ]
        )

        fig.add_trace(bar, row=1, col=1)
        fig.add_trace(table, row=1, col=2)

        fig.update_layout(
            title_text="Dataset Overview",
            margin=dict(l=10, r=10, t=64, b=10),  # Increased top margin for more space
            height=260,
            paper_bgcolor='rgba(30,30,30,0)',
            plot_bgcolor='rgba(30,30,30,0)',
            font=dict(color='white', size=11),
            showlegend=False,
            xaxis=dict(title='Folder', tickfont=dict(color='white')),
            yaxis=dict(title='Count', tickfont=dict(color='white')),
        )
        
        # Render as HTML
        html = pio.to_html(fig, full_html=False, include_plotlyjs='cdn', config={"displayModeBar": False})
        html = html.replace('<body>', '<body style="background-color:transparent; margin:0; padding:0;">')
        html = html.replace('class="plotly-graph-div"', 'class="plotly-graph-div" style="background-color:transparent;"')
        self.stats_view.setHtml(html)