# 📝 NotoPad Pro

**NotoPad Pro** is a professional-grade Python-based text editor designed with Tkinter. It demonstrates clean architecture, advanced UI/UX features, file management, and modern software engineering practices.

---

## 🚀 Features

### ✨ User Interface

- Modern, resizable, theme-switching interface (Light/Dark)
- Font size and style control
- Smart line numbering
- Word and character count
- Zoom in/out with Ctrl + Mouse wheel

### ✏️ Editing Features

- Syntax highlighting for Python
- Auto-indentation
- Bold/Italic/Underline formatting
- Smart Find & Replace (Regex, case sensitivity, whole word)
- Preferences dialog with persistent settings

### 📁 File Operations

- Open, Save, Save As for `.txt`, `.py`, and more
- PDF export (via `reportlab`)
- Auto-save and file backup every 30s
- Recent files tracking via `recent_files.json`
- Print support (cross-platform ready)

### ⚙️ Technical Features

- OOP-based clean architecture (classes: `TextEditor`, `ConfigManager`, etc.)
- Multi-threaded auto-save
- Persistent configuration using `editor_config.ini`
- JSON-based recent file handling
- Cross-platform support (Windows/macOS/Linux)
- Unicode/UTF-8 support
- No drag-and-drop dependency in `.exe` for safe distribution

---

## 📁 Project Structure

```

-📂 NotoPad-Pro/
├── app.py                 # Main source code
├── icon.ico              # App icon
├── app.spec              # PyInstaller build config
├── editor_config.ini     # Stores user preferences
├── recent_files.json     # Recent files log
├── requirements.txt      # Python dependencies 
├── dist/
│   └── app.exe           # Windows executable (build output)
├── build.md              # Build instructions
└── README.md             # This file
```

---

## 🔧 Installation (Run from Source)

### Requirements

```bash
pip install reportlab pyenchant
```

> You may also install `tkinterdnd2` (optional) but drag-and-drop is disabled in the `.exe`.

### Run

```bash
python app.py
```

---

## 📦 Build Instructions (Windows Executable)

See [`build.md`](./build.md) for full build steps.

Quick build command:

```bash
pyinstaller --onefile --windowed --icon=icon.ico app.py
```

---

## 💾 Download the Executable

👉 [Click here to download the latest version](https://github.com/Pushya04/NotoPad-Pro/blob/main/dist/app.exe?raw=true)


> ⚠️ Drag-and-drop is disabled in `.exe` builds for compatibility.

---

## 📷 Screenshots

Add some UI screenshots like:

- Editor with syntax highlighting
- Preferences dialog
- Light/Dark themes
- PDF export in action

---

## 📜 License

MIT License © 2025 Pyaraka Pushyamithra

