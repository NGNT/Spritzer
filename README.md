# Spritzer

`Spritzer` is a desktop tool for working with sprite sheets. It can split an existing sheet into individual sprites, detect sprite boundaries automatically, and assemble imported images into a new sheet.

## Features

- **Automatic sprite detection**  
  Detects sprite regions based on transparency. Detection settings include alpha threshold, minimum sprite size, and optional padding.

- **Grid-based slicing**  
  Supports fixed-width and fixed-height sprite sheets with configurable offsets and spacing.

- **Manual region editing**  
  Lets you create, move, resize, merge, select, and delete sprite regions directly in the preview.

- **Selection preview and animation preview**  
  Displays the selected sprite and can cycle through multiple selected sprites as a simple animation preview.

- **Import and layout tools**  
  Imports multiple sprite images into a new sheet using either uniform cells or original image sizes. Imported sprites can also be reorganized with sorting options.

- **Export options**  
  Exports all sprites or only the current selection. Export filenames support a prefix and configurable start index. Optional trimming removes transparent margins.

- **Undo and redo**  
  Tracks region edits so changes can be reverted when needed.

- **Theme support**  
  Includes multiple built-in themes.

## Controls

### Mouse

- **Click**: Select a sprite
- **Ctrl+Click**: Add or remove a sprite from the selection
- **Drag selected region**: Move a sprite region
- **Drag region edge**: Resize a sprite region
- **Drag on empty space**: Create a new sprite region
- **Shift+Drag**: Create a new sprite region
- **Middle mouse drag**: Pan the canvas
- **Mouse wheel**: Zoom in or out

### Keyboard shortcuts

- `Ctrl+Z`: Undo
- `Ctrl+Y`: Redo
- `Ctrl+A`: Select all sprites
- `Escape`: Clear selection
- `M`: Merge selected regions
- `Delete` / `Backspace`: Remove selected regions
- `F1`: Show keyboard shortcuts

## Getting started

To run `Spritzer` from source, install Python and `PyQt6`.

1. Clone or download this repository.
2. Open a terminal in the project folder.
3. Install dependencies:

   `pip install PyQt6`

4. Run the application:

   `python Spritzer.py`
