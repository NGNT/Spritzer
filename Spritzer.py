import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, QFileDialog, 
                              QVBoxLayout, QHBoxLayout, QWidget, QMenuBar,
                              QSpinBox, QGroupBox, QGraphicsView,
                              QGraphicsScene, QGraphicsPixmapItem, QPushButton,
                              QMessageBox, QLineEdit, QRadioButton, QButtonGroup,
                              QDialog, QDialogButtonBox, QFormLayout, QComboBox,
                              QCheckBox, QScrollArea)
from PyQt6.QtGui import QPixmap, QIcon, QAction, QPainter, QPen, QColor, QImage, QBrush
from PyQt6.QtCore import Qt, QRectF, QRect, QSettings, pyqtSignal, QTimer


# Theme management
APP_SETTINGS_ORGANIZATION = "Spritzer"
APP_SETTINGS_APPLICATION = "Spritzer"
THEME_SETTING_KEY = "appearance/theme"
DEFAULT_THEME_NAME = "Spritzer Dark"
THEME_STYLESHEETS = {
    "Spritzer Dark": "Spritzer.qss",
    "Arcade Glow": "SpritzerArcadeGlow.qss",
    "CRT Amber": "SpritzerCRTAmber.qss",
    "Retro 90s Neon": "SpritzerRetro90sNeon.qss",
    "Sunset Miami": "SpritzerSunsetMiami.qss",
    "Windows 98": "SpritzerWindows98.qss",
}


def load_stylesheet(theme_name: str = DEFAULT_THEME_NAME) -> str:
    """Load a stylesheet by theme name"""
    stylesheet_name = THEME_STYLESHEETS.get(theme_name, THEME_STYLESHEETS[DEFAULT_THEME_NAME])
    stylesheet_path = Path(__file__).with_name(stylesheet_name)

    if not stylesheet_path.exists():
        return ""

    return stylesheet_path.read_text(encoding="utf-8")


def load_saved_theme_name() -> str:
    """Load the saved theme name from settings"""
    settings = QSettings(APP_SETTINGS_ORGANIZATION, APP_SETTINGS_APPLICATION)
    theme_name = settings.value(THEME_SETTING_KEY, DEFAULT_THEME_NAME, str)
    return theme_name if theme_name in THEME_STYLESHEETS else DEFAULT_THEME_NAME


def save_theme_name(theme_name: str) -> None:
    """Save the theme name to settings"""
    if theme_name not in THEME_STYLESHEETS:
        theme_name = DEFAULT_THEME_NAME

    settings = QSettings(APP_SETTINGS_ORGANIZATION, APP_SETTINGS_APPLICATION)
    settings.setValue(THEME_SETTING_KEY, theme_name)


class ZoomableGraphicsView(QGraphicsView):
    """Custom QGraphicsView with zoom and pan capabilities"""
    mouse_pressed = pyqtSignal(object, object)
    mouse_moved = pyqtSignal(object, object)
    mouse_released = pyqtSignal(object, object)

    def __init__(self):
        super().__init__()
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        # Create checkerboard pattern
        checker_size = 8
        pixmap = QPixmap(checker_size * 2, checker_size * 2)
        pixmap.fill(QColor(60, 60, 60))
        painter = QPainter(pixmap)
        painter.fillRect(0, 0, checker_size, checker_size, QColor(43, 43, 43))
        painter.fillRect(checker_size, checker_size, checker_size, checker_size, QColor(43, 43, 43))
        painter.end()
        self.setBackgroundBrush(QBrush(pixmap))

        self.setFrameShape(QGraphicsView.Shape.NoFrame)

        self.zoom_factor = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 10.0
        self.zoom_step = 1.15

        self.is_panning = False
        self.pan_start_pos = None

    def wheelEvent(self, event):
        """Handle mouse wheel for zooming"""
        if event.angleDelta().y() > 0:
            self.zoom_in()
        else:
            self.zoom_out()

    def zoom_in(self):
        """Zoom in by a step"""
        factor = self.zoom_step
        if self.zoom_factor * factor > self.max_zoom:
            return
        self.zoom_factor *= factor
        self.scale(factor, factor)

    def zoom_out(self):
        """Zoom out by a step"""
        factor = 1 / self.zoom_step
        if self.zoom_factor * factor < self.min_zoom:
            return
        self.zoom_factor *= factor
        self.scale(factor, factor)

    def mousePressEvent(self, event):
        """Handle mouse press for panning and selection"""
        if event.button() == Qt.MouseButton.MiddleButton:
            self.is_panning = True
            self.pan_start_pos = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            self.mouse_pressed.emit(scene_pos, event.modifiers())
            super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move for panning and drawing"""
        if self.is_panning and self.pan_start_pos is not None:
            delta = event.pos() - self.pan_start_pos
            self.pan_start_pos = event.pos()

            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            event.accept()
        else:
            if event.buttons() & Qt.MouseButton.LeftButton:
                scene_pos = self.mapToScene(event.pos())
                self.mouse_moved.emit(scene_pos, event.modifiers())
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release to stop panning or drawing"""
        if event.button() == Qt.MouseButton.MiddleButton:
            self.is_panning = False
            self.pan_start_pos = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
        elif event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            self.mouse_released.emit(scene_pos, event.modifiers())
            super().mouseReleaseEvent(event)
        else:
            super().mouseReleaseEvent(event)

    def reset_zoom(self):
        """Reset zoom to 100%"""
        self.resetTransform()
        self.zoom_factor = 1.0


class SpriteSheetGraphicsItem(QGraphicsPixmapItem):
    """Custom graphics item that draws grid overlay"""
    def __init__(self, pixmap=None):
        super().__init__(pixmap)
        self.cell_width = 32
        self.cell_height = 32
        self.offset_x = 0
        self.offset_y = 0
        self.spacing_x = 0
        self.spacing_y = 0
        self.show_grid = False
        self.detected_sprites = []  # List of QRect for detected sprite bounds
        self.grid_sprites = []      # List of QRect for grid sprite bounds
        self.selected_indices = set()
        self.use_detected = False
        self.drag_rect = None

    def set_drag_rect(self, rect):
        self.drag_rect = rect
        self.update()

    def set_grid_sprites(self, sprites):
        self.grid_sprites = sprites
        self.update()

    def set_selected_indices(self, indices):
        self.selected_indices = indices
        self.update()

    def set_cell_size(self, width, height):
        self.cell_width = width
        self.cell_height = height
        self.update()

    def set_offset(self, offset_x, offset_y):
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.update()

    def set_spacing(self, spacing_x, spacing_y):
        self.spacing_x = spacing_x
        self.spacing_y = spacing_y
        self.update()

    def set_show_grid(self, show):
        self.show_grid = show
        self.update()

    def set_detected_sprites(self, sprites):
        self.detected_sprites = sprites
        self.update()

    def set_use_detected(self, use):
        self.use_detected = use
        self.update()

    def paint(self, painter, option, widget):
        # Draw the pixmap first
        super().paint(painter, option, widget)

        # Highlight selected sprites
        if self.selected_indices:
            painter.setBrush(QColor(0, 150, 255, 100))
            painter.setPen(Qt.PenStyle.NoPen)
            sprites = self.detected_sprites if self.use_detected else self.grid_sprites
            for i in self.selected_indices:
                if i < len(sprites):
                    painter.drawRect(sprites[i])

        # Draw detected sprite boundaries
        if self.use_detected and self.detected_sprites:
            pen = QPen(QColor(0, 255, 0, 180))
            pen.setWidth(0)
            pen.setCosmetic(True)
            painter.setPen(pen)

            for rect in self.detected_sprites:
                painter.drawRect(rect)

        # Draw grid overlay if enabled and not using detected mode
        elif self.show_grid and self.pixmap() and not self.pixmap().isNull():
            pen = QPen(QColor(255, 0, 0, 180))
            pen.setWidth(0)  # Cosmetic pen (width doesn't scale with zoom)
            pen.setCosmetic(True)
            painter.setPen(pen)

            pixmap = self.pixmap()
            width = pixmap.width()
            height = pixmap.height()

            # Draw vertical lines with offset and spacing
            x = self.offset_x
            while x <= width:
                painter.drawLine(x, 0, x, height)
                x += self.cell_width + self.spacing_x

            # Draw horizontal lines with offset and spacing
            y = self.offset_y
            while y <= height:
                painter.drawLine(0, y, width, y)
                y += self.cell_height + self.spacing_y

        # Draw currently dragged manual bounding box
        if self.drag_rect:
            pen = QPen(QColor(255, 255, 0, 200))
            pen.setWidth(0)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.setBrush(QColor(255, 255, 0, 50))
            painter.drawRect(self.drag_rect)


class SpriteSheetSplitter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spritzer - Sprite Sheet Splitter")
        self.setGeometry(100, 100, 1360, 760)
        self.setAcceptDrops(True)

        logo_path = Path(__file__).with_name("spritzer.png")
        if logo_path.exists():
            self.setWindowIcon(QIcon(str(logo_path)))

        self.sprite_sheet = None
        self.detected_sprites = []  # Store detected sprite regions
        self.grid_sprites = []      # Store grid sprite regions
        self.selected_indices = set() # Store selected sprite indices
        self.current_file_path = None  # Track current file for saving
        self.imported_sprites = []  # Store imported sprite pixmaps for sorting
        self._selected_theme_name = load_saved_theme_name()

        self.is_dragging_new_sprite = False
        self.drag_start_pos = None

        self.is_moving_sprite = False
        self.is_resizing_sprite = False
        self.active_sprite_idx = -1
        self.resize_handle = None
        self.original_sprite_rect = None
        self.potential_deselect_idx = -1

        self._undo_stack = []
        self._redo_stack = []

        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.advance_animation_frame)
        self.current_anim_frame = 0

        self.init_ui()

        # Create blank canvas at launch
        self.create_blank_canvas(800, 600)

    def _create_settings_group(self, title: str) -> tuple[QGroupBox, QFormLayout]:
        """Helper method to create a consistently styled settings group"""
        group = QGroupBox(title)
        layout = QFormLayout(group)
        layout.setSpacing(6)
        layout.setContentsMargins(10, 10, 10, 8)
        return group, layout

    def _create_row_layout(self, *widgets: QWidget, stretch_index: int | None = None) -> QHBoxLayout:
        """Helper method to create a horizontal row of widgets"""
        row = QHBoxLayout()
        row.setSpacing(6)
        for index, widget in enumerate(widgets):
            row.addWidget(widget, 1 if index == stretch_index else 0)
        return row

    def _apply_theme(self, theme_name: str) -> None:
        """Apply a theme to the application"""
        app = QApplication.instance()
        if app is None:
            return
        save_theme_name(theme_name)
        self._selected_theme_name = theme_name
        app.setStyleSheet(load_stylesheet(theme_name))

    def init_ui(self):
        # Create menu bar
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")

        # Add New action
        new_action = QAction("New Sprite Sheet", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_sprite_sheet)
        file_menu.addAction(new_action)

        # Add Open action
        open_action = QAction("Open Sprite Sheet", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.load_sprite_sheet)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        # Add Import Sprites action
        import_action = QAction("Import Sprites...", self)
        import_action.setShortcut("Ctrl+I")
        import_action.triggered.connect(self.import_sprites)
        file_menu.addAction(import_action)

        file_menu.addSeparator()

        # Add Save action
        save_action = QAction("Save Sprite Sheet", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_sprite_sheet)
        file_menu.addAction(save_action)

        # Add Save As action
        save_as_action = QAction("Save Sprite Sheet As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_sprite_sheet_as)
        file_menu.addAction(save_as_action)

        file_menu.addSeparator()

        # Add Exit action
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Create Edit menu for undo/redo
        edit_menu = menubar.addMenu("Edit")

        self._undo_action = QAction("Undo", self)
        self._undo_action.setShortcut("Ctrl+Z")
        self._undo_action.setEnabled(False)
        self._undo_action.triggered.connect(self.undo)
        edit_menu.addAction(self._undo_action)

        self._redo_action = QAction("Redo", self)
        self._redo_action.setShortcut("Ctrl+Y")
        self._redo_action.setEnabled(False)
        self._redo_action.triggered.connect(self.redo)
        edit_menu.addAction(self._redo_action)

        # Create View menu for theme selection
        view_menu = menubar.addMenu("View")

        theme_menu = view_menu.addMenu("Theme")
        for theme_name in THEME_STYLESHEETS.keys():
            theme_action = QAction(theme_name, self)
            theme_action.triggered.connect(lambda checked, name=theme_name: self._apply_theme(name))
            theme_menu.addAction(theme_action)

        # Create Help menu
        help_menu = menubar.addMenu("Help")
        shortcuts_action = QAction("Keyboard Shortcuts", self)
        shortcuts_action.setShortcut("F1")
        shortcuts_action.triggered.connect(self.show_keyboard_shortcuts)
        help_menu.addAction(shortcuts_action)

        # Create central widget with layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(12)

        # Left panel for settings (wrapped in a scroll area to prevent overflowing window height)
        settings_scroll = QScrollArea()
        settings_scroll.setWidgetResizable(True)
        settings_scroll.setMaximumWidth(620)
        settings_scroll.setMinimumWidth(460)
        settings_scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        left_panel_widget = QWidget()
        left_panel = QVBoxLayout(left_panel_widget)
        left_panel.setContentsMargins(0, 0, 12, 0)
        left_panel.setSpacing(6)

        settings_scroll.setWidget(left_panel_widget)
        root_layout.addWidget(settings_scroll)

        # Right panel for preview (takes remaining space)
        right_panel = QVBoxLayout()
        right_panel.setSpacing(10)
        root_layout.addLayout(right_panel, 1)

        # Logo banner at the top of the left panel
        logo_path = Path(__file__).with_name("spritzer.png")
        if logo_path.exists():
            logo_pixmap = QPixmap(str(logo_path))
            logo_label = QLabel()
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo_label.setPixmap(
                logo_pixmap.scaledToHeight(48, Qt.TransformationMode.SmoothTransformation)
            )
            left_panel.addWidget(logo_label)

        # Create mode selection group box
        mode_group, mode_layout = self._create_settings_group("Detection Mode")

        # Mode radio buttons
        self.mode_button_group = QButtonGroup()
        self.grid_mode_radio = QRadioButton("Grid Mode")
        self.detect_mode_radio = QRadioButton("Auto-Detect Mode")
        self.grid_mode_radio.setChecked(True)

        self.mode_button_group.addButton(self.grid_mode_radio)
        self.mode_button_group.addButton(self.detect_mode_radio)

        self.grid_mode_radio.toggled.connect(self.on_mode_changed)

        # Mode buttons row
        mode_buttons_row = self._create_row_layout(self.grid_mode_radio, self.detect_mode_radio)

        # Alpha threshold control
        self.alpha_spinbox = QSpinBox()
        self.alpha_spinbox.setRange(1, 254)
        self.alpha_spinbox.setValue(10)
        self.alpha_spinbox.setToolTip(
            "Pixels with alpha below this value are treated as transparent.\n"
            "Increase if touching sprites are being merged together."
        )

        # Minimum sprite size control
        self.min_size_spinbox = QSpinBox()
        self.min_size_spinbox.setRange(1, 256)
        self.min_size_spinbox.setValue(2)
        self.min_size_spinbox.setSuffix(" px")
        self.min_size_spinbox.setToolTip("Minimum width and height for a detected region to be kept.")

        # Bounding box padding control
        self.padding_spinbox = QSpinBox()
        self.padding_spinbox.setRange(0, 64)
        self.padding_spinbox.setValue(0)
        self.padding_spinbox.setSuffix(" px")
        self.padding_spinbox.setToolTip("Extra pixels added around each detected sprite's bounding box.")

        # Auto-detect and merge buttons
        self.detect_button = QPushButton("Detect")
        self.detect_button.clicked.connect(self.detect_sprites)
        self.detect_button.setEnabled(False)

        self.merge_button = QPushButton("Merge Selected")
        self.merge_button.clicked.connect(self.merge_sprites)
        self.merge_button.setEnabled(False)
        self.merge_button.setToolTip("Merge multiple selected bounding boxes into one (Shortcut: M).")

        buttons_row = self._create_row_layout(self.detect_button, self.merge_button)

        # Build mode layout using FormLayout
        mode_layout.addRow("Mode:", mode_buttons_row)
        mode_layout.addRow("Alpha Threshold:", self.alpha_spinbox)
        mode_layout.addRow("Min Size:", self.min_size_spinbox)
        mode_layout.addRow("Padding:", self.padding_spinbox)
        mode_layout.addRow("", buttons_row)

        left_panel.addWidget(mode_group)

        # Create controls group box (single column layout)
        controls_group, controls_layout = self._create_settings_group("Sprite Grid Settings")

        # Sprite width control
        self.width_spinbox = QSpinBox()
        self.width_spinbox.setRange(1, 1024)
        self.width_spinbox.setValue(32)
        self.width_spinbox.setSuffix(" px")
        self.width_spinbox.valueChanged.connect(self.update_grid)

        # Sprite height control
        self.height_spinbox = QSpinBox()
        self.height_spinbox.setRange(1, 1024)
        self.height_spinbox.setValue(32)
        self.height_spinbox.setSuffix(" px")
        self.height_spinbox.valueChanged.connect(self.update_grid)

        # Offset X control
        self.offset_x_spinbox = QSpinBox()
        self.offset_x_spinbox.setRange(0, 1024)
        self.offset_x_spinbox.setValue(0)
        self.offset_x_spinbox.setSuffix(" px")
        self.offset_x_spinbox.valueChanged.connect(self.update_grid)

        # Offset Y control
        self.offset_y_spinbox = QSpinBox()
        self.offset_y_spinbox.setRange(0, 1024)
        self.offset_y_spinbox.setValue(0)
        self.offset_y_spinbox.setSuffix(" px")
        self.offset_y_spinbox.valueChanged.connect(self.update_grid)

        # Spacing X control
        self.spacing_x_spinbox = QSpinBox()
        self.spacing_x_spinbox.setRange(0, 256)
        self.spacing_x_spinbox.setValue(0)
        self.spacing_x_spinbox.setSuffix(" px")
        self.spacing_x_spinbox.valueChanged.connect(self.update_grid)

        # Spacing Y control
        self.spacing_y_spinbox = QSpinBox()
        self.spacing_y_spinbox.setRange(0, 256)
        self.spacing_y_spinbox.setValue(0)
        self.spacing_y_spinbox.setSuffix(" px")
        self.spacing_y_spinbox.valueChanged.connect(self.update_grid)

        # Build controls layout using FormLayout
        cell_size_row = self._create_row_layout(self.width_spinbox, QLabel("×"), self.height_spinbox)
        offset_row = self._create_row_layout(self.offset_x_spinbox, self.offset_y_spinbox)
        spacing_row = self._create_row_layout(self.spacing_x_spinbox, self.spacing_y_spinbox)

        self.apply_spacing_button = QPushButton("Apply Spacing to Sheet")
        self.apply_spacing_button.clicked.connect(self.apply_spacing_to_sheet)
        self.apply_spacing_button.setEnabled(False)
        self.apply_spacing_button.setToolTip(
            "Repack current sprites with the current spacing values to create gaps between sprites."
        )

        controls_layout.addRow("Cell Size:", cell_size_row)
        controls_layout.addRow("Offset:", offset_row)
        controls_layout.addRow("Spacing:", spacing_row)
        controls_layout.addRow("Repack:", self.apply_spacing_button)

        left_panel.addWidget(controls_group)

        # Create export group box (single column layout)
        export_group, export_layout = self._create_settings_group("Export Settings")

        # Filename prefix
        self.prefix_input = QLineEdit()
        self.prefix_input.setText("sprite")

        # Start Index control
        self.start_index_spinbox = QSpinBox()
        self.start_index_spinbox.setRange(0, 99999)
        self.start_index_spinbox.setValue(0)
        self.start_index_spinbox.setToolTip("Starting number for the exported sprite filenames.")

        # Trim transparent space combo
        self.trim_combo = QComboBox()
        self.trim_combo.addItems(["Off", "On"])
        self.trim_combo.setToolTip("Automatically crop out empty transparent space tightly around actual pixels during export.")

        # Export button
        self.export_button = QPushButton("Export Sprites")
        self.export_button.clicked.connect(self.export_sprites)
        self.export_button.setEnabled(False)

        # Sort button
        self.sort_button = QPushButton("Sort Sprites")
        self.sort_button.clicked.connect(self.sort_sprites)
        self.sort_button.setEnabled(False)
        self.sort_button.setToolTip("Reorganize imported sprites by size, dimensions, etc.")

        export_layout.addRow("Filename Prefix:", self.prefix_input)
        export_layout.addRow("Start Index:", self.start_index_spinbox)
        export_layout.addRow("Trim Alpha:", self.trim_combo)
        export_layout.addRow("Sort Sprites:", self.sort_button)
        export_layout.addRow("Export Sprites:", self.export_button)

        left_panel.addWidget(export_group)

        # Create preview group box
        preview_group, preview_layout = self._create_settings_group("Selection Preview")
        self.sprite_preview_label = QLabel("No sprite selected")
        self.sprite_preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sprite_preview_label.setMinimumHeight(96)
        self.sprite_preview_label.setStyleSheet("background-color: #000; color: #888; border: 1px solid #444;")
        preview_layout.addRow(self.sprite_preview_label)

        # Animation controls
        self.anim_fps_spinbox = QSpinBox()
        self.anim_fps_spinbox.setRange(1, 60)
        self.anim_fps_spinbox.setValue(8)
        self.anim_fps_spinbox.setSuffix(" fps")
        self.anim_fps_spinbox.valueChanged.connect(self.update_animation_timer)
        self.anim_play_checkbox = QCheckBox("Auto-play")
        self.anim_play_checkbox.setChecked(True)
        self.anim_play_checkbox.toggled.connect(self.update_animation_timer)

        anim_row = self._create_row_layout(self.anim_play_checkbox, self.anim_fps_spinbox)
        preview_layout.addRow("Animation:", anim_row)

        left_panel.addWidget(preview_group)

        # Create info display group box
        info_group, info_layout = self._create_settings_group("Sprite Sheet Info")

        self.info_label = QLabel("No sprite sheet loaded")
        self.info_label.setWordWrap(True)

        info_layout.addRow(self.info_label)

        left_panel.addWidget(info_group)
        left_panel.addStretch()

        # Right panel - Graphics view for the image display with zoom/pan
        # Right panel - Graphics view for the image display with zoom/pan
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(6, 15, 6, 6)

        self.graphics_view = ZoomableGraphicsView()
        self.graphics_view.setObjectName("previewWidget")
        self.graphics_scene = QGraphicsScene()
        self.graphics_view.setScene(self.graphics_scene)
        self.graphics_view.mouse_pressed.connect(self.on_canvas_mouse_pressed)
        self.graphics_view.mouse_moved.connect(self.on_canvas_mouse_moved)
        self.graphics_view.mouse_released.connect(self.on_canvas_mouse_released)

        # Create the sprite sheet graphics item
        self.sprite_item = None

        preview_layout.addWidget(self.graphics_view)

        # Zoom controls
        zoom_layout = QHBoxLayout()
        zoom_layout.setContentsMargins(0, 5, 0, 0)

        self.zoom_out_btn = QPushButton("- Zoom Out")
        self.zoom_out_btn.clicked.connect(self.graphics_view.zoom_out)

        self.zoom_reset_btn = QPushButton("100%")
        self.zoom_reset_btn.clicked.connect(self.graphics_view.reset_zoom)

        self.zoom_in_btn = QPushButton("+ Zoom In")
        self.zoom_in_btn.clicked.connect(self.graphics_view.zoom_in)

        self.zoom_fit_btn = QPushButton("Fit Screen")
        self.zoom_fit_btn.clicked.connect(self.fit_view_to_scene)

        zoom_layout.addStretch()
        zoom_layout.addWidget(self.zoom_out_btn)
        zoom_layout.addWidget(self.zoom_reset_btn)
        zoom_layout.addWidget(self.zoom_in_btn)
        zoom_layout.addWidget(self.zoom_fit_btn)
        zoom_layout.addStretch()

        preview_layout.addLayout(zoom_layout)
        right_panel.addWidget(preview_group)

        hint = QLabel(
            "Click: select  •  Ctrl+Click: multi-select  •  Drag empty / Shift+Drag: new region"
            "  •  Wheel: zoom  •  Mid-drag: pan  •  M: merge  •  Del: remove  •  F1: all shortcuts"
        )
        hint.setObjectName("statusHint")
        self.statusBar().addWidget(hint, 1)

    def fit_view_to_scene(self):
        """Scale the view to perfectly fit the current sprite sheet"""
        if self.sprite_sheet and not self.sprite_sheet.isNull():
            self.graphics_view.reset_zoom()
            self.graphics_view.fitInView(self.graphics_scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def show_keyboard_shortcuts(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Keyboard Shortcuts")
        dlg.setMinimumWidth(440)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(8)

        html = (
            "<style>"
            "h3 { margin: 10px 0 4px 0; }"
            "table { border-collapse: collapse; width: 100%; }"
            "td { padding: 3px 8px; vertical-align: top; }"
            "td:first-child { font-weight: bold; white-space: nowrap; min-width: 160px; }"
            "</style>"
            "<h3>Canvas (Mouse)</h3>"
            "<table>"
            "<tr><td>Click sprite</td><td>Select sprite</td></tr>"
            "<tr><td>Click again</td><td>Deselect sprite</td></tr>"
            "<tr><td>Ctrl+Click</td><td>Add / remove from selection</td></tr>"
            "<tr><td>Drag selected sprite</td><td>Move sprite region</td></tr>"
            "<tr><td>Drag edge of selected sprite</td><td>Resize sprite region</td></tr>"
            "<tr><td>Drag on empty area</td><td>Draw a new sprite region</td></tr>"
            "<tr><td>Shift+Drag on sprite</td><td>Draw a new sprite region</td></tr>"
            "<tr><td>Mouse wheel</td><td>Zoom in / out</td></tr>"
            "<tr><td>Middle-click drag</td><td>Pan canvas</td></tr>"
            "</table>"
            "<h3>Keyboard</h3>"
            "<table>"
            "<tr><td>Ctrl+Z</td><td>Undo</td></tr>"
            "<tr><td>Ctrl+Y</td><td>Redo</td></tr>"
            "<tr><td>Ctrl+A</td><td>Select all sprites</td></tr>"
            "<tr><td>Escape</td><td>Deselect all</td></tr>"
            "<tr><td>M</td><td>Merge selected bounding boxes (Auto-Detect mode only)</td></tr>"
            "<tr><td>Delete / Backspace</td><td>Remove selected sprite regions</td></tr>"
            "<tr><td>F1</td><td>Show this dialog</td></tr>"
            "</table>"
            "<h3>File</h3>"
            "<table>"
            "<tr><td>Ctrl+N</td><td>New sprite sheet</td></tr>"
            "<tr><td>Ctrl+O</td><td>Open sprite sheet</td></tr>"
            "<tr><td>Ctrl+I</td><td>Import sprites</td></tr>"
            "<tr><td>Ctrl+S</td><td>Save sprite sheet</td></tr>"
            "<tr><td>Ctrl+Shift+S</td><td>Save sprite sheet as…</td></tr>"
            "<tr><td>Ctrl+Q</td><td>Exit</td></tr>"
            "</table>"
        )

        label = QLabel(html)
        label.setTextFormat(Qt.TextFormat.RichText)
        label.setWordWrap(True)
        layout.addWidget(label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(dlg.accept)
        layout.addWidget(buttons)

        dlg.exec()

    def _push_undo(self):
        snapshot = {
            'detected_sprites': list(self.detected_sprites),
            'grid_sprites': list(self.grid_sprites),
            'selected_indices': set(self.selected_indices),
            'use_detected': self.detect_mode_radio.isChecked(),
        }
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > 50:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._update_undo_actions()

    def _restore_snapshot(self, snapshot):
        self.detected_sprites = list(snapshot['detected_sprites'])
        self.grid_sprites = list(snapshot['grid_sprites'])
        self.selected_indices = set(snapshot['selected_indices'])
        use_detected = snapshot['use_detected']
        self.grid_mode_radio.blockSignals(True)
        self.detect_mode_radio.blockSignals(True)
        self.detect_mode_radio.setChecked(use_detected)
        self.grid_mode_radio.setChecked(not use_detected)
        self.grid_mode_radio.blockSignals(False)
        self.detect_mode_radio.blockSignals(False)
        grid_enabled = not use_detected
        for sb in [self.width_spinbox, self.height_spinbox,
                   self.offset_x_spinbox, self.offset_y_spinbox]:
            sb.setEnabled(grid_enabled)
        self.spacing_x_spinbox.setEnabled(True)
        self.spacing_y_spinbox.setEnabled(True)
        if self.sprite_item:
            self.sprite_item.set_show_grid(grid_enabled)
            self.sprite_item.set_detected_sprites(self.detected_sprites)
            self.sprite_item.set_grid_sprites(self.grid_sprites)
            self.sprite_item.set_use_detected(use_detected)
            self.sprite_item.set_selected_indices(self.selected_indices)
        self.update_preview_and_export_button()

    def _update_undo_actions(self):
        self._undo_action.setEnabled(bool(self._undo_stack))
        self._redo_action.setEnabled(bool(self._redo_stack))

    def undo(self):
        if not self._undo_stack:
            return
        current = {
            'detected_sprites': list(self.detected_sprites),
            'grid_sprites': list(self.grid_sprites),
            'selected_indices': set(self.selected_indices),
            'use_detected': self.detect_mode_radio.isChecked(),
        }
        self._redo_stack.append(current)
        self._restore_snapshot(self._undo_stack.pop())
        self._update_undo_actions()

    def redo(self):
        if not self._redo_stack:
            return
        current = {
            'detected_sprites': list(self.detected_sprites),
            'grid_sprites': list(self.grid_sprites),
            'selected_indices': set(self.selected_indices),
            'use_detected': self.detect_mode_radio.isChecked(),
        }
        self._undo_stack.append(current)
        self._restore_snapshot(self._redo_stack.pop())
        self._update_undo_actions()

    def on_canvas_mouse_pressed(self, pos, modifiers):
        if not self.sprite_item or not self.sprite_sheet:
            return

        x, y = int(pos.x()), int(pos.y())
        sprites = self.detected_sprites if self.detect_mode_radio.isChecked() else self.grid_sprites

        # Check if we clicked on a resize handle of any selected sprite (auto-detect mode only)
        if self.detect_mode_radio.isChecked():
            for idx in self.selected_indices:
                if idx < len(sprites):
                    rect = sprites[idx]
                    tolerance = max(4, int(4 / self.graphics_view.zoom_factor))

                    left = abs(x - rect.left()) <= tolerance
                    right = abs(x - rect.right()) <= tolerance
                    top = abs(y - rect.top()) <= tolerance
                    bottom = abs(y - rect.bottom()) <= tolerance

                    in_x = rect.left() - tolerance <= x <= rect.right() + tolerance
                    in_y = rect.top() - tolerance <= y <= rect.bottom() + tolerance

                    handle = None
                    if in_x and in_y:
                        if top and left: handle = 'top-left'
                        elif top and right: handle = 'top-right'
                        elif bottom and left: handle = 'bottom-left'
                        elif bottom and right: handle = 'bottom-right'
                        elif top: handle = 'top'
                        elif bottom: handle = 'bottom'
                        elif left: handle = 'left'
                        elif right: handle = 'right'

                    if handle:
                        self.is_resizing_sprite = True
                        self.active_sprite_idx = idx
                        self.resize_handle = handle
                        self.original_sprite_rect = QRect(rect)
                        self.drag_start_pos = (x, y)
                        return

        clicked_idx = -1
        # Reversing so we pick the top-most if they overlap
        for i in reversed(range(len(sprites))):
            if sprites[i].contains(x, y):
                clicked_idx = i
                break

        self.potential_deselect_idx = -1

        # If clicking empty space or holding Shift, start manual slice
        if clicked_idx == -1 or (modifiers & Qt.KeyboardModifier.ShiftModifier):
            self.is_dragging_new_sprite = True
            self.drag_start_pos = (x, y)
            self.sprite_item.set_drag_rect(QRect(x, y, 0, 0))

            # Clear selection if not holding ctrl
            if not (modifiers & Qt.KeyboardModifier.ControlModifier) and self.selected_indices:
                self.selected_indices.clear()
                self.sprite_item.set_selected_indices(self.selected_indices)
                self.update_preview_and_export_button()
        else:
            if modifiers & Qt.KeyboardModifier.ControlModifier or modifiers & Qt.KeyboardModifier.ShiftModifier:
                if clicked_idx in self.selected_indices:
                    self.selected_indices.remove(clicked_idx)
                else:
                    self.selected_indices.add(clicked_idx)
            else:
                if len(self.selected_indices) == 1 and clicked_idx in self.selected_indices:
                    # Mark for potential deselect if we release without dragging
                    self.potential_deselect_idx = clicked_idx
                else:
                    self.selected_indices = {clicked_idx}

                if self.detect_mode_radio.isChecked():
                    self.is_moving_sprite = True
                    self.active_sprite_idx = clicked_idx
                    self.original_sprite_rect = QRect(sprites[clicked_idx])
                    self.drag_start_pos = (x, y)

            self.sprite_item.set_selected_indices(self.selected_indices)
            self.update_preview_and_export_button()

    def on_canvas_mouse_moved(self, pos, modifiers):
        x, y = int(pos.x()), int(pos.y())
        if self.is_dragging_new_sprite and self.drag_start_pos:
            start_x, start_y = self.drag_start_pos
            rect = QRect(
                min(start_x, x), min(start_y, y),
                abs(x - start_x), abs(y - start_y)
            )
            self.sprite_item.set_drag_rect(rect)
        elif self.is_moving_sprite and self.active_sprite_idx != -1 and self.drag_start_pos:
            start_x, start_y = self.drag_start_pos
            if abs(x - start_x) > 2 or abs(y - start_y) > 2:
                self.potential_deselect_idx = -1
                dx = x - start_x
                dy = y - start_y
                rect = QRect(
                    self.original_sprite_rect.x() + dx,
                    self.original_sprite_rect.y() + dy,
                    self.original_sprite_rect.width(),
                    self.original_sprite_rect.height()
                )
                self.detected_sprites[self.active_sprite_idx] = rect
                self.sprite_item.set_detected_sprites(self.detected_sprites)
        elif self.is_resizing_sprite and self.active_sprite_idx != -1 and self.drag_start_pos:
            start_x, start_y = self.drag_start_pos
            if abs(x - start_x) > 2 or abs(y - start_y) > 2:
                rect = QRect(self.original_sprite_rect)
                if 'left' in self.resize_handle:
                    rect.setLeft(min(x, rect.right() - 1))
                elif 'right' in self.resize_handle:
                    rect.setRight(max(x, rect.left() + 1))
                if 'top' in self.resize_handle:
                    rect.setTop(min(y, rect.bottom() - 1))
                elif 'bottom' in self.resize_handle:
                    rect.setBottom(max(y, rect.top() + 1))
                self.detected_sprites[self.active_sprite_idx] = rect
                self.sprite_item.set_detected_sprites(self.detected_sprites)
                if hasattr(self, 'update_preview_and_export_button'):
                    self.update_preview_and_export_button()

    def on_canvas_mouse_released(self, pos, modifiers):
        if self.is_dragging_new_sprite and self.drag_start_pos:
            self.is_dragging_new_sprite = False
            x, y = int(pos.x()), int(pos.y())
            start_x, start_y = self.drag_start_pos

            # Avoid tiny accidentally created rectangles from a single click
            if abs(x - start_x) > 2 and abs(y - start_y) > 2:
                rect = QRect(
                    min(start_x, x), min(start_y, y),
                    abs(x - start_x), abs(y - start_y)
                )

                self._push_undo()

                # We need to switch to Auto-Detect mode to store manual sprites
                if not self.detect_mode_radio.isChecked():
                    self.detect_mode_radio.setChecked(True)

                self.detected_sprites.append(rect)
                self.sprite_item.set_detected_sprites(self.detected_sprites)

                # Automatically select the new sprite
                self.selected_indices.clear()
                self.selected_indices.add(len(self.detected_sprites) - 1)
                self.sprite_item.set_selected_indices(self.selected_indices)
                self.update_preview_and_export_button()

            self.drag_start_pos = None
            self.sprite_item.set_drag_rect(None)
        elif self.is_moving_sprite or self.is_resizing_sprite:
            if self.is_moving_sprite and self.potential_deselect_idx != -1:
                self.selected_indices.clear()
                self.sprite_item.set_selected_indices(self.selected_indices)
                self.update_preview_and_export_button()
            else:
                if self.active_sprite_idx != -1 and self.original_sprite_rect:
                    current_rect = self.detected_sprites[self.active_sprite_idx]
                    if current_rect != self.original_sprite_rect:
                        self.detected_sprites[self.active_sprite_idx] = self.original_sprite_rect
                        self._push_undo()
                        self.detected_sprites[self.active_sprite_idx] = current_rect
                        self.sprite_item.set_detected_sprites(self.detected_sprites)
                        self.update_preview_and_export_button()

            self.is_moving_sprite = False
            self.is_resizing_sprite = False
            self.active_sprite_idx = -1
            self.resize_handle = None
            self.original_sprite_rect = None
            self.potential_deselect_idx = -1

    def update_preview_and_export_button(self):
        if self.selected_indices:
            count = len(self.selected_indices)
            self.export_button.setText(f"Export Selected ({count})")

            # Enable merge if multiple selected and in detect mode
            if hasattr(self, 'merge_button'):
                self.merge_button.setEnabled(count > 1 and self.detect_mode_radio.isChecked())

            self.current_anim_frame = 0
            self.update_animation_frame()
            self.update_animation_timer()
        else:
            self.export_button.setText("Export Sprites")
            if hasattr(self, 'merge_button'):
                self.merge_button.setEnabled(False)
            self.sprite_preview_label.clear()
            self.sprite_preview_label.setText("No sprite selected")
            if hasattr(self, 'animation_timer') and self.animation_timer.isActive():
                self.animation_timer.stop()

    def update_animation_timer(self):
        if len(self.selected_indices) > 1 and self.anim_play_checkbox.isChecked():
            fps = self.anim_fps_spinbox.value()
            self.animation_timer.start(1000 // fps)
        else:
            if hasattr(self, 'animation_timer'):
                self.animation_timer.stop()

    def advance_animation_frame(self):
        if not self.selected_indices:
            return
        self.current_anim_frame = (self.current_anim_frame + 1) % len(self.selected_indices)
        self.update_animation_frame()

    def update_animation_frame(self):
        if not self.selected_indices:
            return
        sprites = self.detected_sprites if self.detect_mode_radio.isChecked() else self.grid_sprites
        sorted_indices = sorted(self.selected_indices)

        if len(sorted_indices) > 1:
            idx_to_preview = sorted_indices[self.current_anim_frame % len(sorted_indices)]
        else:
            idx_to_preview = sorted_indices[0]

        if idx_to_preview < len(sprites):
            rect = sprites[idx_to_preview]
            pixmap = self.sprite_sheet.copy(rect)

            # Scale pixmap for preview
            if hasattr(self, 'sprite_preview_label'):
                available_size = self.sprite_preview_label.size()
                scaled = pixmap.scaled(
                    available_size.width() - 4, available_size.height() - 4,
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.FastTransformation
                )
                self.sprite_preview_label.setPixmap(scaled)

    def load_sprite_sheet(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Sprite Sheet",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
        )

        if file_path:
            self.load_sprite_sheet_from_file(file_path)

    def load_sprite_sheet_from_file(self, file_path):
        self.sprite_sheet = QPixmap(file_path)
        if not self.sprite_sheet.isNull():
            # Clear previous scene items
            self.graphics_scene.clear()

            # Create new sprite item and add to scene
            self.sprite_item = SpriteSheetGraphicsItem(self.sprite_sheet)
            self.graphics_scene.addItem(self.sprite_item)

            # Set scene rect to pixmap bounds
            self.graphics_scene.setSceneRect(QRectF(self.sprite_sheet.rect()))

            # Reset zoom and fit in view
            self.graphics_view.reset_zoom()
            self.graphics_view.fitInView(self.graphics_scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

            self.setWindowTitle(f"Spritzer - {file_path}")
            self.update_grid()

            # Enable buttons
            self.export_button.setEnabled(True)
            self.detect_button.setEnabled(True)
            self.apply_spacing_button.setEnabled(True)

            # Reset to grid mode
            self.grid_mode_radio.setChecked(True)
            self.detected_sprites = []
            self.grid_sprites = []
            self.selected_indices = set()
            self.imported_sprites = []
            self._undo_stack.clear()
            self._redo_stack.clear()
            self._update_undo_actions()
            if hasattr(self, 'sprite_preview_label'):
                self.update_preview_and_export_button()

    def merge_sprites(self):
        """Merge selected sprites into one bounding box"""
        if len(self.selected_indices) < 2 or not self.detect_mode_radio.isChecked():
            return

        self._push_undo()
        sprites_to_merge = [self.detected_sprites[i] for i in self.selected_indices]

        min_x = min(rect.left() for rect in sprites_to_merge)
        min_y = min(rect.top() for rect in sprites_to_merge)
        max_x = max(rect.right() for rect in sprites_to_merge)
        max_y = max(rect.bottom() for rect in sprites_to_merge)

        merged_rect = QRect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)

        # Remove old sprites
        self.detected_sprites = [s for i, s in enumerate(self.detected_sprites) if i not in self.selected_indices]

        # Add new merged sprite
        self.detected_sprites.append(merged_rect)
        if self.sprite_item:
            self.sprite_item.set_detected_sprites(self.detected_sprites)

        # Select the new merged sprite
        self.selected_indices.clear()
        self.selected_indices.add(len(self.detected_sprites) - 1)
        if self.sprite_item:
            self.sprite_item.set_selected_indices(self.selected_indices)

        self.update_preview_and_export_button()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].isLocalFile():
                ext = urls[0].fileName().lower().split('.')[-1]
                if ext in ['png', 'jpg', 'jpeg', 'bmp', 'gif']:
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            file_path = urls[0].toLocalFile()
            self.load_sprite_sheet_from_file(file_path)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_A and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            sprites = self.detected_sprites if self.detect_mode_radio.isChecked() else self.grid_sprites
            self.selected_indices = set(range(len(sprites)))
            if self.sprite_item:
                self.sprite_item.set_selected_indices(self.selected_indices)
            self.update_preview_and_export_button()
            event.accept()
        elif event.key() == Qt.Key.Key_Escape:
            self.selected_indices.clear()
            if self.sprite_item:
                self.sprite_item.set_selected_indices(self.selected_indices)
            self.update_preview_and_export_button()
            event.accept()
        elif event.key() == Qt.Key.Key_M:
            self.merge_sprites()
            event.accept()
        elif event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            if self.selected_indices:
                self._push_undo()
                if self.detect_mode_radio.isChecked():
                    self.detected_sprites = [s for i, s in enumerate(self.detected_sprites) if i not in self.selected_indices]
                    if self.sprite_item:
                        self.sprite_item.set_detected_sprites(self.detected_sprites)
                else:
                    self.grid_sprites = [s for i, s in enumerate(self.grid_sprites) if i not in self.selected_indices]
                    if self.sprite_item:
                        self.sprite_item.set_grid_sprites(self.grid_sprites)

                self.selected_indices.clear()
                if self.sprite_item:
                    self.sprite_item.set_selected_indices(self.selected_indices)
                self.update_preview_and_export_button()
            event.accept()
        else:
            super().keyPressEvent(event)

    def create_blank_canvas(self, width, height):
        """Create a blank transparent canvas"""
        # Create a transparent image
        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)

        self.sprite_sheet = QPixmap.fromImage(image)
        self.current_file_path = None

        # Clear previous scene items
        self.graphics_scene.clear()

        # Create new sprite item and add to scene
        self.sprite_item = SpriteSheetGraphicsItem(self.sprite_sheet)
        self.graphics_scene.addItem(self.sprite_item)

        # Set scene rect to pixmap bounds
        self.graphics_scene.setSceneRect(QRectF(self.sprite_sheet.rect()))

        # Reset zoom and fit in view
        self.graphics_view.reset_zoom()
        self.graphics_view.fitInView(self.graphics_scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

        self.setWindowTitle("Spritzer - New Sprite Sheet")
        self.update_grid()

        # Disable export and detect until sprites are added
        self.export_button.setEnabled(False)
        self.detect_button.setEnabled(False)
        self.apply_spacing_button.setEnabled(False)

        # Reset to grid mode
        self.grid_mode_radio.setChecked(True)
        self.detected_sprites = []
        self.grid_sprites = []
        self.selected_indices = set()
        self.imported_sprites = []
        self._undo_stack.clear()
        self._redo_stack.clear()
        if hasattr(self, '_undo_action'):
            self._update_undo_actions()
        if hasattr(self, 'sprite_preview_label'):
            self.update_preview_and_export_button()

    def update_grid(self):
        """Update the grid overlay with current cell dimensions"""
        cell_width = self.width_spinbox.value()
        cell_height = self.height_spinbox.value()
        offset_x = self.offset_x_spinbox.value()
        offset_y = self.offset_y_spinbox.value()
        spacing_x = self.spacing_x_spinbox.value()
        spacing_y = self.spacing_y_spinbox.value()

        if self.sprite_item:
            self.sprite_item.set_cell_size(cell_width, cell_height)
            self.sprite_item.set_offset(offset_x, offset_y)
            self.sprite_item.set_spacing(spacing_x, spacing_y)

            # Enable grid if an image is loaded
            if self.sprite_sheet and not self.sprite_sheet.isNull():
                self.sprite_item.set_show_grid(True)

                # Calculate and display sprite info
                available_width = self.sprite_sheet.width() - offset_x
                available_height = self.sprite_sheet.height() - offset_y

                if cell_width + spacing_x > 0:
                    cols = (available_width + spacing_x) // (cell_width + spacing_x)
                else:
                    cols = 0

                if cell_height + spacing_y > 0:
                    rows = (available_height + spacing_y) // (cell_height + spacing_y)
                else:
                    rows = 0

                self.grid_sprites = []
                for r in range(rows):
                    for c in range(cols):
                        x = offset_x + c * (cell_width + spacing_x)
                        y = offset_y + r * (cell_height + spacing_y)
                        self.grid_sprites.append(QRect(x, y, cell_width, cell_height))

                self.sprite_item.set_grid_sprites(self.grid_sprites)
                self.selected_indices.clear()
                self.sprite_item.set_selected_indices(self.selected_indices)
                if hasattr(self, 'sprite_preview_label'):
                    self.update_preview_and_export_button()

                total_sprites = cols * rows

                self.info_label.setText(
                    f"Sheet Size: {self.sprite_sheet.width()}x{self.sprite_sheet.height()} | "
                    f"Grid: {cols}x{rows} | "
                    f"Total Sprites: {total_sprites} | "
                    f"Sprite Size: {cell_width}x{cell_height}"
                )
                self.info_label.setStyleSheet("QLabel { color: #00ff00; }")

    def export_sprites(self):
        """Export individual sprites from the sprite sheet"""
        if not self.sprite_sheet or self.sprite_sheet.isNull():
            QMessageBox.warning(self, "No Sprite Sheet", "Please load a sprite sheet first.")
            return

        # Ask user to select output directory
        output_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            "",
            QFileDialog.Option.ShowDirsOnly
        )

        if not output_dir:
            return

        prefix = self.prefix_input.text() or "sprite"
        start_index = self.start_index_spinbox.value()
        trim_enabled = hasattr(self, 'trim_combo') and self.trim_combo.currentText() == "On"
        alpha_threshold = self.alpha_spinbox.value()

        sprites_to_export = []
        source_sprites = self.detected_sprites if self.detect_mode_radio.isChecked() else self.grid_sprites

        if self.selected_indices:
            sprites_to_export = [source_sprites[i] for i in sorted(self.selected_indices)]
        else:
            sprites_to_export = source_sprites

        if not sprites_to_export:
            QMessageBox.warning(
                self,
                "No Sprites",
                "There are no sprites to export."
            )
            return

        sprite_count = start_index
        exported_count = 0
        for sprite_rect in sprites_to_export:
            # Extract sprite
            sprite = self.sprite_sheet.copy(sprite_rect)

            if trim_enabled:
                image = sprite.toImage().convertToFormat(QImage.Format.Format_ARGB32)
                w, h = image.width(), image.height()
                ptr = image.bits()
                ptr.setsize(h * w * 4)
                raw = bytearray(ptr)

                min_x, min_y, max_x, max_y = w, h, -1, -1

                for y in range(h):
                    row_offset = y * w * 4
                    for x in range(w):
                        if raw[row_offset + x * 4 + 3] >= alpha_threshold:
                            if x < min_x: min_x = x
                            if x > max_x: max_x = x
                            if y < min_y: min_y = y
                            if y > max_y: max_y = y

                if max_x >= min_x and max_y >= min_y:
                    sprite = sprite.copy(QRect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1))
                else:
                    # Entirely transparent, skip to avoid blank artifacts
                    continue

            # Generate filename
            filename = f"{prefix}_{sprite_count:03d}.png"
            filepath = os.path.join(output_dir, filename)

            # Save sprite
            sprite.save(filepath, "PNG")
            sprite_count += 1
            exported_count += 1

        # Show success message
        QMessageBox.information(
            self,
            "Export Complete",
            f"Successfully exported {exported_count} sprites to:\n{output_dir}"
        )

    def apply_spacing_to_sheet(self):
        """Repack current sprite regions with user-selected spacing."""
        if not self.sprite_sheet or self.sprite_sheet.isNull():
            QMessageBox.warning(self, "No Sprite Sheet", "Please load or import sprites first.")
            return

        spacing_x = self.spacing_x_spinbox.value()
        spacing_y = self.spacing_y_spinbox.value()

        if spacing_x == 0 and spacing_y == 0:
            QMessageBox.information(
                self,
                "No Spacing Applied",
                "Set Spacing X or Spacing Y above 0, then run this action again."
            )
            return

        source_sprites = self.detected_sprites if self.detect_mode_radio.isChecked() else self.grid_sprites
        if not source_sprites and self.sprite_sheet:
            self.update_grid()
            source_sprites = self.grid_sprites

        if not source_sprites:
            QMessageBox.warning(
                self,
                "No Sprites",
                "No sprite regions are available to repack. Use grid settings or auto-detect first."
            )
            return

        sprites = []
        for rect in source_sprites:
            sprite = self.sprite_sheet.copy(rect)
            if not sprite.isNull():
                sprites.append(sprite)

        if not sprites:
            QMessageBox.warning(self, "No Sprites", "Could not extract sprite regions from the current sheet.")
            return

        self.imported_sprites = sprites.copy()

        # Pack sprites into a near-square fixed-column grid
        sprite_count = len(sprites)
        estimated_cols = max(1, int((sprite_count ** 0.5) + 0.999))
        rows = [
            sprites[i:i + estimated_cols]
            for i in range(0, sprite_count, estimated_cols)
        ]

        canvas_width = 0
        canvas_height = 0
        row_heights = []

        for row in rows:
            row_width = sum(s.width() for s in row) + spacing_x * (len(row) - 1)
            row_height = max(s.height() for s in row)
            canvas_width = max(canvas_width, row_width)
            row_heights.append(row_height)

        canvas_height = sum(row_heights) + spacing_y * (len(rows) - 1)

        result = QImage(canvas_width, canvas_height, QImage.Format.Format_ARGB32)
        result.fill(Qt.GlobalColor.transparent)
        painter = QPainter(result)

        y_offset = 0
        sprite_regions = []

        for row_idx, row in enumerate(rows):
            x_offset = 0
            row_height = row_heights[row_idx]

            for sprite in row:
                painter.drawPixmap(x_offset, y_offset, sprite)
                sprite_regions.append(QRect(x_offset, y_offset, sprite.width(), sprite.height()))
                x_offset += sprite.width() + spacing_x

            y_offset += row_height + spacing_y

        painter.end()

        self.sprite_sheet = QPixmap.fromImage(result)
        self.sprite_item.setPixmap(self.sprite_sheet)
        self.graphics_scene.setSceneRect(QRectF(self.sprite_sheet.rect()))

        self.graphics_view.reset_zoom()
        self.graphics_view.fitInView(self.graphics_scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

        self.detected_sprites = sprite_regions
        self.grid_sprites = []
        self.selected_indices.clear()

        if self.sprite_item:
            self.sprite_item.set_detected_sprites(sprite_regions)
            self.sprite_item.set_selected_indices(self.selected_indices)

        self.detect_mode_radio.setChecked(True)
        self.on_mode_changed()

        self.export_button.setEnabled(True)
        self.detect_button.setEnabled(True)
        self.sort_button.setEnabled(True)

        QMessageBox.information(
            self,
            "Spacing Applied",
            f"Repacked {len(sprite_regions)} sprites with spacing X={spacing_x}, Y={spacing_y}."
        )

    def detect_sprites(self):
        """Automatically detect sprite boundaries using alpha channel analysis"""
        if not self.sprite_sheet or self.sprite_sheet.isNull():
            QMessageBox.warning(self, "No Sprite Sheet", "Please load a sprite sheet first.")
            return

        alpha_threshold = self.alpha_spinbox.value()
        min_size = self.min_size_spinbox.value()
        padding = self.padding_spinbox.value()

        # Ensure ARGB32 format so byte layout is always A=byte3, R=byte2, G=byte1, B=byte0
        image = self.sprite_sheet.toImage().convertToFormat(QImage.Format.Format_ARGB32)
        width = image.width()
        height = image.height()

        # Read all pixels into a flat bytearray once - far faster than per-pixel pixelColor()
        ptr = image.bits()
        ptr.setsize(height * width * 4)
        raw = bytearray(ptr)

        def alpha_at(x, y):
            # ARGB32: each pixel is 4 bytes; alpha is at offset +3
            return raw[(y * width + x) * 4 + 3]

        visited = bytearray(width * height)  # flat array, faster than list-of-lists
        detected_regions = []

        def flood_fill(start_x, start_y):
            min_x = max_x = start_x
            min_y = max_y = start_y

            stack = [(start_x, start_y)]
            visited[start_y * width + start_x] = 1

            while stack:
                x, y = stack.pop()

                if x < min_x: min_x = x
                if x > max_x: max_x = x
                if y < min_y: min_y = y
                if y > max_y: max_y = y

                for nx, ny in ((x, y - 1), (x, y + 1), (x - 1, y), (x + 1, y)):
                    if 0 <= nx < width and 0 <= ny < height:
                        idx = ny * width + nx
                        if not visited[idx] and alpha_at(nx, ny) >= alpha_threshold:
                            visited[idx] = 1
                            stack.append((nx, ny))

            return min_x, min_y, max_x, max_y

        # Scan the image for sprite regions
        for y in range(height):
            for x in range(width):
                idx = y * width + x
                if not visited[idx] and alpha_at(x, y) >= alpha_threshold:
                    min_x, min_y, max_x, max_y = flood_fill(x, y)

                    w = max_x - min_x + 1
                    h = max_y - min_y + 1

                    # Apply min size filter
                    if w >= min_size and h >= min_size:
                        # Apply padding, clamped to image bounds
                        px = max(0, min_x - padding)
                        py = max(0, min_y - padding)
                        px2 = min(width - 1, max_x + padding)
                        py2 = min(height - 1, max_y + padding)
                        detected_regions.append(QRect(px, py, px2 - px + 1, py2 - py + 1))

        if not detected_regions:
            QMessageBox.warning(
                self,
                "No Sprites Detected",
                "No sprites were detected. Try lowering the Alpha Threshold or checking "
                "that your sprite sheet has a transparent background."
            )
            return

        # Sort sprites by position (top to bottom, left to right)
        detected_regions.sort(key=lambda r: (r.y(), r.x()))

        self._push_undo()
        self.detected_sprites = detected_regions

        # Update the graphics item
        if self.sprite_item:
            self.sprite_item.set_detected_sprites(detected_regions)
            self.selected_indices.clear()
            self.sprite_item.set_selected_indices(self.selected_indices)
            self.detect_mode_radio.setChecked(True)
            self.on_mode_changed()

        # Update info
        self.info_label.setText(
            f"Sheet Size: {width}x{height} | "
            f"Detected Sprites: {len(detected_regions)} "
            f"(threshold: {alpha_threshold}, min: {min_size}px, padding: {padding}px)"
        )
        self.info_label.setStyleSheet("QLabel { color: #00ff00; }")

        QMessageBox.information(
            self,
            "Detection Complete",
            f"Detected {len(detected_regions)} sprites!"
        )

    def on_mode_changed(self):
        """Handle mode switching between grid and auto-detect"""
        self.selected_indices.clear()
        if self.sprite_item:
            self.sprite_item.set_selected_indices(self.selected_indices)
            use_detected = self.detect_mode_radio.isChecked()
            self.sprite_item.set_use_detected(use_detected)

            # Enable/disable grid controls based on mode
            grid_enabled = not use_detected
            self.width_spinbox.setEnabled(grid_enabled)
            self.height_spinbox.setEnabled(grid_enabled)
            self.offset_x_spinbox.setEnabled(grid_enabled)
            self.offset_y_spinbox.setEnabled(grid_enabled)
            self.spacing_x_spinbox.setEnabled(True)
            self.spacing_y_spinbox.setEnabled(True)

            # Update info display
            if use_detected and self.detected_sprites:
                self.info_label.setText(
                    f"Sheet Size: {self.sprite_sheet.width()}x{self.sprite_sheet.height()} | "
                    f"Detected Sprites: {len(self.detected_sprites)}"
                )
            elif self.sprite_sheet:
                self.update_grid()

        if hasattr(self, 'sprite_preview_label'):
            self.update_preview_and_export_button()

    def new_sprite_sheet(self):
        """Create a new blank sprite sheet with user-defined dimensions"""
        dialog = QDialog(self)
        dialog.setWindowTitle("New Sprite Sheet")

        layout = QFormLayout(dialog)

        width_spin = QSpinBox()
        width_spin.setRange(1, 4096)
        width_spin.setValue(800)
        width_spin.setSuffix(" px")

        height_spin = QSpinBox()
        height_spin.setRange(1, 4096)
        height_spin.setValue(600)
        height_spin.setSuffix(" px")

        layout.addRow("Width:", width_spin)
        layout.addRow("Height:", height_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.create_blank_canvas(width_spin.value(), height_spin.value())

    def import_sprites(self):
        """Import individual sprite images and place them on the canvas"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Import Sprites",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
        )

        if not file_paths:
            return

        # Load all sprites first
        sprites = []
        max_width = 0
        max_height = 0

        for file_path in file_paths:
            sprite = QPixmap(file_path)
            if not sprite.isNull():
                sprites.append(sprite)
                max_width = max(max_width, sprite.width())
                max_height = max(max_height, sprite.height())

        if not sprites:
            QMessageBox.warning(self, "No Sprites", "No valid sprite images were found.")
            return

        # Ask user if they want to use original dimensions or uniform cell grid
        reply = QMessageBox.question(
            self,
            "Import Settings",
            f"Detected max sprite size: {max_width}×{max_height} px\n"
            f"Current cell size: {self.width_spinbox.value()}×{self.height_spinbox.value()} px\n\n"
            "Yes: Each sprite keeps its original dimensions (variable cell sizes)\n"
            "No: All sprites fit into uniform grid cells (fixed cell size)\n\n"
            "Import at original sprite sizes?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )

        use_original_size = (reply == QMessageBox.StandardButton.Yes)
        spacing_x = self.spacing_x_spinbox.value()
        spacing_y = self.spacing_y_spinbox.value()

        if use_original_size:
            # Row-based packing: each sprite keeps its own dimensions
            # Store imported sprites for later sorting
            self.imported_sprites = sprites.copy()

            # Pack sprites into a near-square fixed-column grid
            sprite_count = len(sprites)
            estimated_cols = max(1, int((sprite_count ** 0.5) + 0.999))
            rows = [
                sprites[i:i + estimated_cols]
                for i in range(0, sprite_count, estimated_cols)
            ]

            # Calculate canvas dimensions
            canvas_width = 0
            canvas_height = 0
            row_heights = []

            for row in rows:
                row_width = sum(s.width() for s in row) + spacing_x * (len(row) - 1)
                row_height = max(s.height() for s in row)
                canvas_width = max(canvas_width, row_width)
                row_heights.append(row_height)

            canvas_height = sum(row_heights) + spacing_y * (len(rows) - 1)

            # Create canvas
            result = QImage(canvas_width, canvas_height, QImage.Format.Format_ARGB32)
            result.fill(Qt.GlobalColor.transparent)
            painter = QPainter(result)

            # Draw sprites row by row
            y_offset = 0
            sprite_regions = []  # Store sprite bounds for detection

            for row_idx, row in enumerate(rows):
                x_offset = 0
                row_height = row_heights[row_idx]

                for sprite in row:
                    # Draw sprite at its natural size
                    painter.drawPixmap(x_offset, y_offset, sprite)

                    # Store sprite region
                    sprite_regions.append(QRect(x_offset, y_offset, sprite.width(), sprite.height()))

                    x_offset += sprite.width() + spacing_x

                y_offset += row_height + spacing_y

            painter.end()

            # Update the sprite sheet
            self.sprite_sheet = QPixmap.fromImage(result)
            self.sprite_item.setPixmap(self.sprite_sheet)

            # Update scene rect
            self.graphics_scene.setSceneRect(QRectF(self.sprite_sheet.rect()))

            # Fit in view
            self.graphics_view.reset_zoom()
            self.graphics_view.fitInView(self.graphics_scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

            # Store detected regions and switch to auto-detect mode to show individual cells
            self.detected_sprites = sprite_regions
            if self.sprite_item:
                self.sprite_item.set_detected_sprites(sprite_regions)
                self.detect_mode_radio.setChecked(True)
                self.on_mode_changed()

            # Enable export and detect buttons
            self.export_button.setEnabled(True)
            self.detect_button.setEnabled(True)
            self.sort_button.setEnabled(True)  # Enable sort for variable-size imports
            self.apply_spacing_button.setEnabled(True)

            QMessageBox.information(
                self,
                "Import Complete",
                f"Imported {len(sprites)} sprites with original dimensions\n"
                f"Sheet size: {canvas_width}×{canvas_height} px\n"
                f"Rows: {len(rows)}\n"
                f"Variable cell sizes preserved\n\n"
                f"Switched to Auto-Detect mode to show individual sprite boundaries."
            )

        else:
            # Uniform grid mode: all cells are the same size
            # Clear imported sprites (not applicable for uniform grid)
            self.imported_sprites = []
            cell_width = self.width_spinbox.value()
            cell_height = self.height_spinbox.value()

            # Calculate optimal grid layout
            sprite_count = len(sprites)
            cols = int((sprite_count ** 0.5) + 0.999)
            rows = (sprite_count + cols - 1) // cols

            # Calculate canvas dimensions
            canvas_width = cols * cell_width + (cols - 1) * spacing_x
            canvas_height = rows * cell_height + (rows - 1) * spacing_y

            # Create canvas
            result = QImage(canvas_width, canvas_height, QImage.Format.Format_ARGB32)
            result.fill(Qt.GlobalColor.transparent)
            painter = QPainter(result)

            row = 0
            col = 0

            for sprite in sprites:
                # Calculate position
                x = col * (cell_width + spacing_x)
                y = row * (cell_height + spacing_y)

                # Scale sprite if too large
                if sprite.width() > cell_width or sprite.height() > cell_height:
                    sprite = sprite.scaled(
                        cell_width, cell_height,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )

                # Center sprite in cell
                dx = (cell_width - sprite.width()) // 2
                dy = (cell_height - sprite.height()) // 2

                painter.drawPixmap(x + dx, y + dy, sprite)

                col += 1
                if col >= cols:
                    col = 0
                    row += 1

            painter.end()

            # Update the sprite sheet
            self.sprite_sheet = QPixmap.fromImage(result)
            self.sprite_item.setPixmap(self.sprite_sheet)

            # Update scene rect
            self.graphics_scene.setSceneRect(QRectF(self.sprite_sheet.rect()))

            # Fit in view
            self.graphics_view.reset_zoom()
            self.graphics_view.fitInView(self.graphics_scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

            # Update cell size and grid
            self.width_spinbox.setValue(cell_width)
            self.height_spinbox.setValue(cell_height)
            self.update_grid()

            # Enable export and detect buttons
            self.export_button.setEnabled(True)
            self.detect_button.setEnabled(True)
            self.apply_spacing_button.setEnabled(True)

            QMessageBox.information(
                self,
                "Import Complete",
                f"Imported {len(sprites)} sprites into uniform grid\n"
                f"Sheet size: {canvas_width}×{canvas_height} px\n"
                f"Grid: {cols}×{rows}\n"
                f"Cell size: {cell_width}×{cell_height} px"
            )

    def save_sprite_sheet(self):
        """Save the current sprite sheet"""
        if self.current_file_path:
            self.sprite_sheet.save(self.current_file_path, "PNG")
            QMessageBox.information(self, "Saved", f"Sprite sheet saved to:\n{self.current_file_path}")
        else:
            self.save_sprite_sheet_as()

    def save_sprite_sheet_as(self):
        """Save the sprite sheet to a new file"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Sprite Sheet",
            "",
            "PNG Image (*.png);;All Files (*)"
        )

        if file_path:
            if not file_path.lower().endswith('.png'):
                file_path += '.png'

            self.sprite_sheet.save(file_path, "PNG")
            self.current_file_path = file_path
            self.setWindowTitle(f"Spritzer - {file_path}")
            QMessageBox.information(self, "Saved", f"Sprite sheet saved to:\n{file_path}")

    def sort_sprites(self):
        """Sort and reorganize imported sprites based on user-selected criteria"""
        if not self.imported_sprites:
            QMessageBox.warning(
                self,
                "No Sprites to Sort",
                "Sorting is only available for sprites imported with original dimensions.\n\n"
                "Import sprites and choose 'Yes' when asked about original sprite sizes."
            )
            return

        # Create sort options dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Sort Sprites")
        layout = QFormLayout(dialog)

        # Sorting criteria combo box
        criteria_combo = QComboBox()
        criteria_combo.addItems([
            "Area (Largest First)",
            "Area (Smallest First)",
            "Width (Widest First)",
            "Width (Narrowest First)",
            "Height (Tallest First)",
            "Height (Shortest First)",
            "Aspect Ratio (Landscape First)",
            "Aspect Ratio (Portrait First)",
            "Perimeter (Largest First)",
            "Perimeter (Smallest First)"
        ])
        layout.addRow("Sort By:", criteria_combo)

        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        # Get selected sorting criteria
        criteria = criteria_combo.currentText()

        # Sort sprites based on criteria
        sorted_sprites = self.imported_sprites.copy()

        if "Area (Largest First)" in criteria:
            sorted_sprites.sort(key=lambda s: s.width() * s.height(), reverse=True)
        elif "Area (Smallest First)" in criteria:
            sorted_sprites.sort(key=lambda s: s.width() * s.height(), reverse=False)
        elif "Width (Widest First)" in criteria:
            sorted_sprites.sort(key=lambda s: s.width(), reverse=True)
        elif "Width (Narrowest First)" in criteria:
            sorted_sprites.sort(key=lambda s: s.width(), reverse=False)
        elif "Height (Tallest First)" in criteria:
            sorted_sprites.sort(key=lambda s: s.height(), reverse=True)
        elif "Height (Shortest First)" in criteria:
            sorted_sprites.sort(key=lambda s: s.height(), reverse=False)
        elif "Aspect Ratio (Landscape First)" in criteria:
            sorted_sprites.sort(key=lambda s: s.width() / max(s.height(), 1), reverse=True)
        elif "Aspect Ratio (Portrait First)" in criteria:
            sorted_sprites.sort(key=lambda s: s.width() / max(s.height(), 1), reverse=False)
        elif "Perimeter (Largest First)" in criteria:
            sorted_sprites.sort(key=lambda s: (s.width() + s.height()) * 2, reverse=True)
        elif "Perimeter (Smallest First)" in criteria:
            sorted_sprites.sort(key=lambda s: (s.width() + s.height()) * 2, reverse=False)

        # Re-pack sprites using the same algorithm as import
        spacing_x = self.spacing_x_spinbox.value()
        spacing_y = self.spacing_y_spinbox.value()

        sprite_count = len(sorted_sprites)
        estimated_cols = max(1, int((sprite_count ** 0.5) + 0.999))

        # Pack sprites into a near-square fixed-column grid
        rows = [
            sorted_sprites[i:i + estimated_cols]
            for i in range(0, sprite_count, estimated_cols)
        ]

        # Calculate canvas dimensions
        canvas_width = 0
        canvas_height = 0
        row_heights = []

        for row in rows:
            row_width = sum(s.width() for s in row) + spacing_x * (len(row) - 1)
            row_height = max(s.height() for s in row)
            canvas_width = max(canvas_width, row_width)
            row_heights.append(row_height)

        canvas_height = sum(row_heights) + spacing_y * (len(rows) - 1)

        # Create canvas
        result = QImage(canvas_width, canvas_height, QImage.Format.Format_ARGB32)
        result.fill(Qt.GlobalColor.transparent)
        painter = QPainter(result)

        # Draw sprites row by row
        y_offset = 0
        sprite_regions = []

        for row_idx, row in enumerate(rows):
            x_offset = 0
            row_height = row_heights[row_idx]

            for sprite in row:
                # Draw sprite at its natural size
                painter.drawPixmap(x_offset, y_offset, sprite)

                # Store sprite region
                sprite_regions.append(QRect(x_offset, y_offset, sprite.width(), sprite.height()))

                x_offset += sprite.width() + spacing_x

            y_offset += row_height + spacing_y

        painter.end()

        # Update the sprite sheet
        self.sprite_sheet = QPixmap.fromImage(result)
        self.sprite_item.setPixmap(self.sprite_sheet)

        # Update scene rect
        self.graphics_scene.setSceneRect(QRectF(self.sprite_sheet.rect()))

        # Fit in view
        self.graphics_view.reset_zoom()
        self.graphics_view.fitInView(self.graphics_scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

        # Update detected regions
        self.detected_sprites = sprite_regions
        if self.sprite_item:
            self.sprite_item.set_detected_sprites(sprite_regions)

        QMessageBox.information(
            self,
            "Sort Complete",
            f"Sprites reorganized by: {criteria}\n"
            f"Sheet size: {canvas_width}×{canvas_height} px\n"
            f"Rows: {len(rows)}"
        )


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(load_stylesheet(load_saved_theme_name()))
    window = SpriteSheetSplitter()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
