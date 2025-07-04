import os
import sys
import json
import threading
import re
import webbrowser
from datetime import datetime
from tkinter import *
from tkinter import filedialog, colorchooser, font, simpledialog, messagebox, ttk
from tkinter.messagebox import *
from tkinter.filedialog import *
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
import configparser

# Optional imports with fallback
try:
    import enchant
    SPELLCHECK_AVAILABLE = True
except ImportError:
    SPELLCHECK_AVAILABLE = False

# Enhanced drag and drop import with better error handling for PyInstaller

DRAG_DROP_AVAILABLE = False
try:
    # Check if we're running as a PyInstaller bundle
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller bundle - disable drag and drop
        DRAG_DROP_AVAILABLE = False
        print("PyInstaller detected - drag and drop disabled")
    else:
        # Running as normal Python script
        from tkinterdnd2 import DND_FILES, TkinterDnD
        DRAG_DROP_AVAILABLE = True
        print("tkinterdnd2 loaded successfully")
except ImportError:
    DRAG_DROP_AVAILABLE = False
    print("tkinterdnd2 not available - drag and drop functionality disabled")
except Exception as e:
    DRAG_DROP_AVAILABLE = False
    print(f"Failed to load tkinterdnd2: {e}")

# Constants
APP_NAME = "NotoPad Pro"
APP_VERSION = "1.0"
CONFIG_FILE = "editor_config.ini"
RECENT_FILES_FILE = "recent_files.json"
MAX_RECENT = 10
AUTO_SAVE_INTERVAL = 30  # seconds
BACKUP_INTERVAL = 300  # 5 minutes

class ConfigManager:
    """Manages application configuration and settings"""
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config_file = CONFIG_FILE
        self.load_config()
    
    def load_config(self):
        """Load configuration from file"""
        try:
            self.config.read(self.config_file)
            if not self.config.has_section('EDITOR'):
                self.config.add_section('EDITOR')
            if not self.config.has_section('APPEARANCE'):
                self.config.add_section('APPEARANCE')
        except Exception as e:
            print(f"Error loading config: {e}")
            self.create_default_config()
    
    def create_default_config(self):
        """Create default configuration"""
        self.config.add_section('EDITOR')
        self.config.set('EDITOR', 'font_name', 'Consolas')
        self.config.set('EDITOR', 'font_size', '12')
        self.config.set('EDITOR', 'theme', 'light')
        self.config.set('EDITOR', 'word_wrap', 'True')
        self.config.set('EDITOR', 'auto_save', 'True')
        self.config.set('EDITOR', 'line_numbers', 'True')
        
        self.config.add_section('APPEARANCE')
        self.config.set('APPEARANCE', 'window_width', '1000')
        self.config.set('APPEARANCE', 'window_height', '700')
        self.config.set('APPEARANCE', 'theme_color', 'blue')
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                self.config.write(f)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get(self, section, option, fallback=None):
        """Get configuration value"""
        try:
            return self.config.get(section, option)
        except:
            return fallback
    
    def set(self, section, option, value):
        """Set configuration value"""
        try:
            self.config.set(section, option, str(value))
        except:
            pass

class LineNumberCanvas(Canvas):
    """Custom canvas widget for displaying line numbers"""
    def __init__(self, master, text_widget, **kwargs):
        super().__init__(master, width=50, **kwargs)
        self.text_widget = text_widget
        self.bind_events()
        self.redraw()
    
    def bind_events(self):
        """Bind events to update line numbers"""
        self.text_widget.bind('<KeyRelease>', self.redraw)
        self.text_widget.bind('<MouseWheel>', self.redraw)
        self.text_widget.bind('<ButtonRelease>', self.redraw)
        self.text_widget.bind('<Configure>', self.redraw)
    
    def redraw(self, event=None):
        """Redraw line numbers"""
        try:
            self.delete('all')
            i = self.text_widget.index('@0,0')
            while True:
                dline = self.text_widget.dlineinfo(i)
                if dline is None:
                    break
                y = dline[1]
                linenum = str(i).split('.')[0]
                self.create_text(35, y, anchor='ne', text=linenum, 
                               fill='gray', font=('Courier', 9))
                i = self.text_widget.index(f'{i}+1line')
        except Exception as e:
            print(f"Error redrawing line numbers: {e}")

class SearchDialog:
    """Advanced search and replace dialog"""
    def __init__(self, parent, text_widget):
        self.parent = parent
        self.text_widget = text_widget
        self.search_window = None
        self.last_search = ""
        self.current_match = None
        
    def show_dialog(self):
        """Show search/replace dialog"""
        if self.search_window:
            self.search_window.lift()
            return
            
        self.search_window = Toplevel(self.parent)
        self.search_window.title("Find & Replace")
        self.search_window.geometry("400x200")
        self.search_window.resizable(False, False)
        
        # Search frame
        search_frame = Frame(self.search_window)
        search_frame.pack(fill=X, padx=10, pady=5)
        
        Label(search_frame, text="Find:").pack(anchor=W)
        self.search_entry = Entry(search_frame, width=50)
        self.search_entry.pack(fill=X, pady=2)
        
        Label(search_frame, text="Replace:").pack(anchor=W)
        self.replace_entry = Entry(search_frame, width=50)
        self.replace_entry.pack(fill=X, pady=2)
        
        # Options frame
        options_frame = Frame(self.search_window)
        options_frame.pack(fill=X, padx=10, pady=5)
        
        self.match_case = BooleanVar()
        self.whole_word = BooleanVar()
        
        Checkbutton(options_frame, text="Match Case", variable=self.match_case).pack(anchor=W)
        Checkbutton(options_frame, text="Whole Word", variable=self.whole_word).pack(anchor=W)
        
        # Buttons frame
        buttons_frame = Frame(self.search_window)
        buttons_frame.pack(fill=X, padx=10, pady=5)
        
        Button(buttons_frame, text="Find Next", command=self.find_next).pack(side=LEFT, padx=2)
        Button(buttons_frame, text="Replace", command=self.replace_current).pack(side=LEFT, padx=2)
        Button(buttons_frame, text="Replace All", command=self.replace_all).pack(side=LEFT, padx=2)
        Button(buttons_frame, text="Close", command=self.close_dialog).pack(side=RIGHT, padx=2)
        
        self.search_window.protocol("WM_DELETE_WINDOW", self.close_dialog)
        self.search_entry.focus()
    
    def find_next(self):
        """Find next occurrence"""
        search_text = self.search_entry.get()
        if not search_text:
            return
            
        start_pos = self.text_widget.index(INSERT)
        if search_text != self.last_search:
            start_pos = "1.0"
        
        flags = []
        if not self.match_case.get():
            flags.append('nocase')
        if self.whole_word.get():
            flags.append('exact')
        
        pos = self.text_widget.search(search_text, start_pos, stopindex=END, 
                                     count=None, *flags)
        if pos:
            self.text_widget.mark_set(INSERT, pos)
            self.text_widget.see(pos)
            end_pos = f"{pos}+{len(search_text)}c"
            self.text_widget.tag_remove(SEL, "1.0", END)
            self.text_widget.tag_add(SEL, pos, end_pos)
            self.current_match = (pos, end_pos)
            self.last_search = search_text
        else:
            messagebox.showinfo("Search", "Text not found")
    
    def replace_current(self):
        """Replace current selection"""
        if self.current_match:
            replace_text = self.replace_entry.get()
            self.text_widget.delete(self.current_match[0], self.current_match[1])
            self.text_widget.insert(self.current_match[0], replace_text)
            self.find_next()
    
    def replace_all(self):
        """Replace all occurrences"""
        search_text = self.search_entry.get()
        replace_text = self.replace_entry.get()
        
        if not search_text:
            return
        
        content = self.text_widget.get("1.0", END)
        count = 0
        
        if not self.match_case.get():
            if self.whole_word.get():
                import re
                pattern = r'\b' + re.escape(search_text) + r'\b'
                content, count = re.subn(pattern, replace_text, content, flags=re.IGNORECASE)
            else:
                count = content.lower().count(search_text.lower())
                content = content.replace(search_text, replace_text)
        else:
            if self.whole_word.get():
                import re
                pattern = r'\b' + re.escape(search_text) + r'\b'
                content, count = re.subn(pattern, replace_text, content)
            else:
                count = content.count(search_text)
                content = content.replace(search_text, replace_text)
        
        self.text_widget.delete("1.0", END)
        self.text_widget.insert("1.0", content)
        messagebox.showinfo("Replace All", f"Replaced {count} occurrences")
    
    def close_dialog(self):
        """Close search dialog"""
        self.search_window.destroy()
        self.search_window = None

class TextEditor:
    """Main Text Editor Application"""
    def __init__(self):
        self.config_manager = ConfigManager()
        self.recent_files = []
        self.current_file = None
        self.auto_save_thread = None
        self.is_modified = False
        self.search_dialog = None
        
        self.setup_window()
        self.setup_variables()
        self.setup_widgets()
        self.setup_menu()
        self.setup_bindings()
        self.load_recent_files()
        self.load_settings()
        self.start_auto_save()
        
    def setup_window(self):
        """Setup main window"""
        # Always use regular Tk for better PyInstaller compatibility
        self.window = Tk()
        # If drag and drop is available and we're not in PyInstaller, enable it
        if DRAG_DROP_AVAILABLE and not getattr(sys, 'frozen', False):
            try:
                self.window.destroy()
                self.window = TkinterDnD.Tk()
                print("TkinterDnD initialized successfully")
            except Exception as e:
                print(f"Failed to initialize TkinterDnD: {e}")
                self.window = Tk()
                # Move global declaration to the top of the function, not inside except
                # Instead, set the variable as nonlocal or use a setter method
                # But since DRAG_DROP_AVAILABLE is only used for feature toggling, just set it here
                globals()['DRAG_DROP_AVAILABLE'] = False
        self.window.title(f"{APP_NAME} v{APP_VERSION}")
        # Try to set icon, but don't fail if it doesn't exist
        try:
            if os.path.exists('icon.ico'):
                self.window.iconbitmap('icon.ico')
        except Exception as e:
            print(f"Could not load icon: {e}")
        # Window geometry
        width = int(self.config_manager.get('APPEARANCE', 'window_width', '1000'))
        height = int(self.config_manager.get('APPEARANCE', 'window_height', '700'))
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = int((screen_width - width) / 2)
        y = int((screen_height - height) / 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
        self.window.minsize(600, 400)
        # Window protocol
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_variables(self):
        """Setup tkinter variables"""
        self.font_name = StringVar(value=self.config_manager.get('EDITOR', 'font_name', 'Consolas'))
        self.font_size = StringVar(value=self.config_manager.get('EDITOR', 'font_size', '12'))
        self.theme_var = StringVar(value=self.config_manager.get('EDITOR', 'theme', 'light'))
        self.word_wrap_var = BooleanVar(value=self.config_manager.get('EDITOR', 'word_wrap', 'True') == 'True')
        self.line_numbers_var = BooleanVar(value=self.config_manager.get('EDITOR', 'line_numbers', 'True') == 'True')
        self.auto_save_var = BooleanVar(value=self.config_manager.get('EDITOR', 'auto_save', 'True') == 'True')
    
    def setup_widgets(self):
        """Setup main widgets"""
        # Main frame
        self.main_frame = Frame(self.window)
        self.main_frame.pack(fill=BOTH, expand=True)
        # Toolbar
        self.setup_toolbar()
        # Text area frame
        self.text_frame = Frame(self.main_frame)
        self.text_frame.pack(fill=BOTH, expand=True, padx=5, pady=5)
        # Text area with scrollbars
        self.text_area = Text(
            self.text_frame,
            font=(self.font_name.get(), int(self.font_size.get())),
            undo=True,
            wrap='word' if self.word_wrap_var.get() else 'none',
            tabs=('1c', '2c', '3c', '4c'),
            selectbackground='lightblue',
            selectforeground='black',
            insertbackground='black',
            relief=SUNKEN,
            bd=1
        )
        # Scrollbars
        self.v_scrollbar = Scrollbar(self.text_frame, orient=VERTICAL, command=self.text_area.yview)
        self.h_scrollbar = Scrollbar(self.text_frame, orient=HORIZONTAL, command=self.text_area.xview)
        self.text_area.configure(yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)
        # Line numbers
        self.line_numbers = LineNumberCanvas(self.text_frame, self.text_area, bg='#f0f0f0')
        # Pack widgets
        if self.line_numbers_var.get():
            self.line_numbers.pack(side=LEFT, fill=Y)
        self.text_area.pack(side=LEFT, fill=BOTH, expand=True)
        self.v_scrollbar.pack(side=RIGHT, fill=Y)
        self.h_scrollbar.pack(side=BOTTOM, fill=X)
        # Status bar
        self.setup_status_bar()
        # Drag and drop - only if available and not in PyInstaller
        if DRAG_DROP_AVAILABLE and not getattr(sys, 'frozen', False):
            try:
                self.text_area.drop_target_register(DND_FILES)
                self.text_area.dnd_bind('<<Drop>>', self.on_drop)
                print("Drag and drop enabled")
            except Exception as e:
                print(f"Failed to setup drag and drop: {e}")
                globals()['DRAG_DROP_AVAILABLE'] = False
    
    def setup_toolbar(self):
        """Setup toolbar with buttons"""
        self.toolbar = Frame(self.main_frame, relief=RAISED, bd=1)
        self.toolbar.pack(fill=X, padx=5, pady=2)
        
        # File operations
        Button(self.toolbar, text="New", command=self.new_file, width=8).pack(side=LEFT, padx=2)
        Button(self.toolbar, text="Open", command=self.open_file, width=8).pack(side=LEFT, padx=2)
        Button(self.toolbar, text="Save", command=self.save_file, width=8).pack(side=LEFT, padx=2)
        
        # Separator
        Frame(self.toolbar, width=2, bg='gray').pack(side=LEFT, fill=Y, padx=5)
        
        # Edit operations
        Button(self.toolbar, text="Undo", command=self.undo, width=8).pack(side=LEFT, padx=2)
        Button(self.toolbar, text="Redo", command=self.redo, width=8).pack(side=LEFT, padx=2)
        
        # Separator
        Frame(self.toolbar, width=2, bg='gray').pack(side=LEFT, fill=Y, padx=5)
        
        # Font controls
        Label(self.toolbar, text="Font:").pack(side=LEFT, padx=2)
        
        self.font_combo = ttk.Combobox(self.toolbar, textvariable=self.font_name, 
                                      values=sorted(font.families()), width=12)
        self.font_combo.pack(side=LEFT, padx=2)
        self.font_combo.bind('<<ComboboxSelected>>', self.change_font)
        
        self.size_spin = Spinbox(self.toolbar, from_=8, to=72, width=5, 
                                textvariable=self.font_size, command=self.change_font)
        self.size_spin.pack(side=LEFT, padx=2)
        
        # Separator
        Frame(self.toolbar, width=2, bg='gray').pack(side=LEFT, fill=Y, padx=5)
        
        # Text formatting
        Button(self.toolbar, text="B", font=('Arial', 10, 'bold'), 
               command=self.toggle_bold, width=3).pack(side=LEFT, padx=1)
        Button(self.toolbar, text="I", font=('Arial', 10, 'italic'), 
               command=self.toggle_italic, width=3).pack(side=LEFT, padx=1)
        Button(self.toolbar, text="U", font=('Arial', 10, 'underline'), 
               command=self.toggle_underline, width=3).pack(side=LEFT, padx=1)
        
        # Color button
        Button(self.toolbar, text="Color", command=self.change_color, width=8).pack(side=LEFT, padx=2)
        
        # Show drag and drop status
        status_text = "Drag & Drop: "
        if getattr(sys, 'frozen', False):
            status_text += "Disabled (PyInstaller)"
        elif DRAG_DROP_AVAILABLE:
            status_text += "Enabled"
        else:
            status_text += "Disabled"
        
        Label(self.toolbar, text=f"({status_text})", fg='red' if not DRAG_DROP_AVAILABLE else 'green', 
              font=('Arial', 8)).pack(side=RIGHT, padx=5)
    
    def setup_status_bar(self):
        """Setup status bar"""
        self.status_frame = Frame(self.main_frame)
        self.status_frame.pack(fill=X, side=BOTTOM)
        
        self.status_bar = Label(self.status_frame, text="Ready", anchor=W, relief=SUNKEN, bd=1)
        self.status_bar.pack(side=LEFT, fill=X, expand=True)
        
        self.cursor_position = Label(self.status_frame, text="Ln 1, Col 1", anchor=E, relief=SUNKEN, bd=1)
        self.cursor_position.pack(side=RIGHT)
        
        self.word_count = Label(self.status_frame, text="Words: 0", anchor=E, relief=SUNKEN, bd=1)
        self.word_count.pack(side=RIGHT)
    
    def setup_menu(self):
        """Setup menu bar"""
        self.menu_bar = Menu(self.window)
        self.window.config(menu=self.menu_bar)
        
        # File menu
        self.file_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        self.file_menu.add_command(label="New", command=self.new_file, accelerator="Ctrl+N")
        self.file_menu.add_command(label="Open", command=self.open_file, accelerator="Ctrl+O")
        self.file_menu.add_command(label="Save", command=self.save_file, accelerator="Ctrl+S")
        self.file_menu.add_command(label="Save As", command=self.save_as_file, accelerator="Ctrl+Shift+S")
        self.file_menu.add_separator()
        
        # Recent files submenu
        self.recent_menu = Menu(self.file_menu, tearoff=0)
        self.file_menu.add_cascade(label="Recent Files", menu=self.recent_menu)
        
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Export to PDF", command=self.export_pdf)
        self.file_menu.add_command(label="Print", command=self.print_file, accelerator="Ctrl+P")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.on_closing, accelerator="Ctrl+Q")
        
        # Edit menu
        self.edit_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Edit", menu=self.edit_menu)
        self.edit_menu.add_command(label="Undo", command=self.undo, accelerator="Ctrl+Z")
        self.edit_menu.add_command(label="Redo", command=self.redo, accelerator="Ctrl+Y")
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Cut", command=self.cut, accelerator="Ctrl+X")
        self.edit_menu.add_command(label="Copy", command=self.copy, accelerator="Ctrl+C")
        self.edit_menu.add_command(label="Paste", command=self.paste, accelerator="Ctrl+V")
        self.edit_menu.add_command(label="Select All", command=self.select_all, accelerator="Ctrl+A")
        self.edit_menu.add_separator()
        self.edit_menu.add_command(label="Find & Replace", command=self.show_find_replace, accelerator="Ctrl+F")
        self.edit_menu.add_command(label="Go to Line", command=self.goto_line, accelerator="Ctrl+G")
        
        # View menu
        self.view_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="View", menu=self.view_menu)
        self.view_menu.add_checkbutton(label="Word Wrap", variable=self.word_wrap_var, 
                                      command=self.toggle_word_wrap)
        self.view_menu.add_checkbutton(label="Line Numbers", variable=self.line_numbers_var, 
                                      command=self.toggle_line_numbers)
        self.view_menu.add_separator()
        self.view_menu.add_command(label="Zoom In", command=self.zoom_in, accelerator="Ctrl++")
        self.view_menu.add_command(label="Zoom Out", command=self.zoom_out, accelerator="Ctrl+-")
        self.view_menu.add_command(label="Reset Zoom", command=self.reset_zoom, accelerator="Ctrl+0")
        self.view_menu.add_separator()
        self.view_menu.add_command(label="Toggle Theme", command=self.toggle_theme)
        
        # Tools menu
        self.tools_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Tools", menu=self.tools_menu)
        self.tools_menu.add_command(label="Word Count", command=self.show_word_count)
        self.tools_menu.add_command(label="Character Count", command=self.show_char_count)
        if SPELLCHECK_AVAILABLE:
            self.tools_menu.add_command(label="Spell Check", command=self.spell_check)
        self.tools_menu.add_separator()
        self.tools_menu.add_command(label="Preferences", command=self.show_preferences)
        
        # Help menu
        self.help_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Help", menu=self.help_menu)
        self.help_menu.add_command(label="Keyboard Shortcuts", command=self.show_shortcuts)
        self.help_menu.add_command(label="About", command=self.show_about)
    
    def setup_bindings(self):
        """Setup keyboard bindings"""
        # File operations
        self.window.bind('<Control-n>', lambda e: self.new_file())
        self.window.bind('<Control-o>', lambda e: self.open_file())
        self.window.bind('<Control-s>', lambda e: self.save_file())
        self.window.bind('<Control-S>', lambda e: self.save_as_file())
        self.window.bind('<Control-q>', lambda e: self.on_closing())
        self.window.bind('<Control-p>', lambda e: self.print_file())
        
        # Edit operations
        self.window.bind('<Control-z>', lambda e: self.undo())
        self.window.bind('<Control-y>', lambda e: self.redo())
        self.window.bind('<Control-x>', lambda e: self.cut())
        self.window.bind('<Control-c>', lambda e: self.copy())
        self.window.bind('<Control-v>', lambda e: self.paste())
        self.window.bind('<Control-a>', lambda e: self.select_all())
        self.window.bind('<Control-f>', lambda e: self.show_find_replace())
        self.window.bind('<Control-g>', lambda e: self.goto_line())
        
        # View operations
        self.window.bind('<Control-plus>', lambda e: self.zoom_in())
        self.window.bind('<Control-minus>', lambda e: self.zoom_out())
        self.window.bind('<Control-0>', lambda e: self.reset_zoom())
        
        # Text area bindings
        self.text_area.bind('<KeyRelease>', self.on_text_change)
        self.text_area.bind('<Button-1>', self.on_text_change)
        self.text_area.bind('<MouseWheel>', self.on_text_change)
        self.text_area.bind('<Control-MouseWheel>', self.on_mouse_wheel)
        
        # Auto-complete and syntax highlighting
        self.text_area.bind('<KeyRelease>', self.on_key_release)
    
    # Drag and drop handler
    def on_drop(self, event):
        """Handle file drop"""
        if not DRAG_DROP_AVAILABLE:
            return
        
        files = event.data.split()
        if files:
            file_path = files[0]
            # Remove curly braces if present
            if file_path.startswith('{') and file_path.endswith('}'):
                file_path = file_path[1:-1]
            
            self.open_file(file_path)
    
    # File operations
    def new_file(self):
        """Create new file"""
        if self.is_modified:
            if not self.ask_save_changes():
                return
        
        self.text_area.delete(1.0, END)
        self.current_file = None
        self.is_modified = False
        self.window.title(f"{APP_NAME} - Untitled")
        self.update_status("New file created")
    
    def open_file(self, filepath=None):
        """Open file"""
        if self.is_modified:
            if not self.ask_save_changes():
                return
        
        if not filepath:
            filepath = filedialog.askopenfilename(
                title="Open File",
                filetypes=[
                    ("Text files", "*.txt"),
                    ("Python files", "*.py"),
                    ("All files", "*.*")
                ]
            )
        
        if filepath:
            try:
                with open(filepath, 'r', encoding='utf-8') as file:
                    content = file.read()
                    self.text_area.delete(1.0, END)
                    self.text_area.insert(1.0, content)
                
                self.current_file = filepath
                self.is_modified = False
                self.window.title(f"{APP_NAME} - {os.path.basename(filepath)}")
                self.add_recent_file(filepath)
                self.update_status(f"Opened: {os.path.basename(filepath)}")
                self.highlight_syntax()
                
            except Exception as e:
                messagebox.showerror("Error", f"Could not open file: {str(e)}")
    
    def save_file(self):
        """Save current file"""
        if self.current_file:
            try:
                with open(self.current_file, 'w', encoding='utf-8') as file:
                    file.write(self.text_area.get(1.0, END + '-1c'))
                
                self.is_modified = False
                self.update_status(f"Saved: {os.path.basename(self.current_file)}")
                self.window.title(f"{APP_NAME} - {os.path.basename(self.current_file)}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file: {str(e)}")
        else:
            self.save_as_file()
    
    def save_as_file(self):
        """Save file with new name"""
        filepath = filedialog.asksaveasfilename(
            title="Save As",
            defaultextension=".txt",
            filetypes=[
                ("Text files", "*.txt"),
                ("Python files", "*.py"),
                ("All files", "*.*")
            ]
        )
        
        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as file:
                    file.write(self.text_area.get(1.0, END + '-1c'))
                
                self.current_file = filepath
                self.is_modified = False
                self.window.title(f"{APP_NAME} - {os.path.basename(filepath)}")
                self.add_recent_file(filepath)
                self.update_status(f"Saved as: {os.path.basename(filepath)}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Could not save file: {str(e)}")
    
    def ask_save_changes(self):
        """Ask user to save changes before closing"""
        result = messagebox.askyesnocancel(
            "Save Changes",
            "Do you want to save changes to the current document?"
        )
        
        if result is True:
            self.save_file()
            return True
        elif result is False:
            return True
        else:
            return False
    
    # Edit operations
    def undo(self):
        """Undo last action"""
        try:
            self.text_area.edit_undo()
            self.update_status("Undo")
        except:
            pass
    
    def redo(self):
        """Redo last undone action"""
        try:
            self.text_area.edit_redo()
            self.update_status("Redo")
        except:
            pass
    
    def cut(self):
        """Cut selected text"""
        try:
            self.text_area.event_generate("<<Cut>>")
            self.update_status("Cut")
        except:
            pass
    
    def copy(self):
        """Copy selected text"""
        try:
            self.text_area.event_generate("<<Copy>>")
            self.update_status("Copy")
        except:
            pass
    
    def paste(self):
        """Paste text from clipboard"""
        try:
            self.text_area.event_generate("<<Paste>>")
            self.update_status("Paste")
        except:
            pass
    
    def select_all(self):
        """Select all text"""
        self.text_area.tag_add(SEL, "1.0", END)
        self.text_area.mark_set(INSERT, "1.0")
        self.text_area.see(INSERT)
        self.update_status("Select All")
    
    def show_find_replace(self):
        """Show find and replace dialog"""
        if not self.search_dialog:
            self.search_dialog = SearchDialog(self.window, self.text_area)
        self.search_dialog.show_dialog()
    
    def goto_line(self):
        """Go to specific line"""
        try:
            line_num = simpledialog.askinteger("Go to Line", "Enter line number:")
            if line_num:
                self.text_area.mark_set(INSERT, f"{line_num}.0")
                self.text_area.see(INSERT)
                self.update_status(f"Went to line {line_num}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not go to line: {str(e)}")
    
    # View operations
    def toggle_word_wrap(self):
        """Toggle word wrap"""
        if self.word_wrap_var.get():
            self.text_area.config(wrap='word')
        else:
            self.text_area.config(wrap='none')
        self.update_status("Word wrap toggled")
    
    def toggle_line_numbers(self):
        """Toggle line numbers"""
        if self.line_numbers_var.get():
            self.line_numbers.pack(side=LEFT, fill=Y, before=self.text_area)
        else:
            self.line_numbers.pack_forget()
        self.update_status("Line numbers toggled")
    
    def zoom_in(self):
        """Increase font size"""
        current_size = int(self.font_size.get())
        if current_size < 72:
            self.font_size.set(str(current_size + 1))
            self.change_font()
    
    def zoom_out(self):
        """Decrease font size"""
        current_size = int(self.font_size.get())
        if current_size > 8:
            self.font_size.set(str(current_size - 1))
            self.change_font()
    
    def reset_zoom(self):
        """Reset font size to default"""
        self.font_size.set("12")
        self.change_font()
    
    def change_font(self, event=None):
        """Change font"""
        try:
            font_tuple = (self.font_name.get(), int(self.font_size.get()))
            self.text_area.config(font=font_tuple)
            self.update_status(f"Font changed to {self.font_name.get()} {self.font_size.get()}")
        except Exception as e:
            print(f"Error changing font: {e}")
    
    def toggle_theme(self):
        """Toggle between light and dark theme"""
        if self.theme_var.get() == 'light':
            self.theme_var.set('dark')
            self.apply_dark_theme()
        else:
            self.theme_var.set('light')
            self.apply_light_theme()
    
    def apply_light_theme(self):
        """Apply light theme"""
        self.text_area.config(bg='white', fg='black', insertbackground='black')
        self.window.config(bg='white')
        self.main_frame.config(bg='white')
        self.text_frame.config(bg='white')
        self.update_status("Light theme applied")
    
    def apply_dark_theme(self):
        """Apply dark theme"""
        self.text_area.config(bg='#2b2b2b', fg='#ffffff', insertbackground='white')
        self.window.config(bg='#2b2b2b')
        self.main_frame.config(bg='#2b2b2b')
        self.text_frame.config(bg='#2b2b2b')
        self.update_status("Dark theme applied")
    
    # Text formatting
    def toggle_bold(self):
        """Toggle bold formatting"""
        try:
            current_tags = self.text_area.tag_names(INSERT)
            if 'bold' in current_tags:
                self.text_area.tag_remove('bold', SEL_FIRST, SEL_LAST)
            else:
                self.text_area.tag_add('bold', SEL_FIRST, SEL_LAST)
                self.text_area.tag_config('bold', font=(self.font_name.get(), int(self.font_size.get()), 'bold'))
        except:
            pass
    
    def toggle_italic(self):
        """Toggle italic formatting"""
        try:
            current_tags = self.text_area.tag_names(INSERT)
            if 'italic' in current_tags:
                self.text_area.tag_remove('italic', SEL_FIRST, SEL_LAST)
            else:
                self.text_area.tag_add('italic', SEL_FIRST, SEL_LAST)
                self.text_area.tag_config('italic', font=(self.font_name.get(), int(self.font_size.get()), 'italic'))
        except:
            pass
    
    def toggle_underline(self):
        """Toggle underline formatting"""
        try:
            current_tags = self.text_area.tag_names(INSERT)
            if 'underline' in current_tags:
                self.text_area.tag_remove('underline', SEL_FIRST, SEL_LAST)
            else:
                self.text_area.tag_add('underline', SEL_FIRST, SEL_LAST)
                self.text_area.tag_config('underline', underline=True)
        except:
            pass
    
    def change_color(self):
        """Change text color"""
        try:
            color = colorchooser.askcolor(title="Choose Color")[1]
            if color:
                self.text_area.tag_add('color', SEL_FIRST, SEL_LAST)
                self.text_area.tag_config('color', foreground=color)
        except:
            pass
    
    # Tools and utilities
    def show_word_count(self):
        """Show word count dialog"""
        content = self.text_area.get(1.0, END)
        words = len(content.split())
        lines = content.count('\n')
        chars = len(content)
        chars_no_spaces = len(content.replace(' ', '').replace('\n', ''))
        
        messagebox.showinfo("Word Count Statistics", 
                          f"Words: {words}\n"
                          f"Lines: {lines}\n"
                          f"Characters: {chars}\n"
                          f"Characters (no spaces): {chars_no_spaces}")
    
    def show_char_count(self):
        """Show character count"""
        content = self.text_area.get(1.0, END)
        chars = len(content)
        messagebox.showinfo("Character Count", f"Total characters: {chars}")
    
    def spell_check(self):
        """Basic spell check functionality"""
        if not SPELLCHECK_AVAILABLE:
            messagebox.showwarning("Spell Check", "Spell check is not available. Please install pyenchant.")
            return
        
        try:
            import enchant
            dictionary = enchant.Dict("en_US")
            content = self.text_area.get(1.0, END)
            words = re.findall(r'\b\w+\b', content)
            
            misspelled = [word for word in words if not dictionary.check(word)]
            
            if misspelled:
                messagebox.showinfo("Spell Check", f"Misspelled words found: {len(misspelled)}\n"
                                                  f"First few: {', '.join(misspelled[:10])}")
            else:
                messagebox.showinfo("Spell Check", "No misspelled words found!")
        except Exception as e:
            messagebox.showerror("Spell Check Error", f"Error during spell check: {str(e)}")
    
    # Export and printing
    def export_pdf(self):
        """Export document to PDF"""
        if not self.current_file:
            self.save_as_file()
            if not self.current_file:
                return
        
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".pdf",
                filetypes=[("PDF files", "*.pdf")]
            )
            
            if filename:
                content = self.text_area.get(1.0, END)
                
                c = canvas.Canvas(filename, pagesize=letter)
                width, height = letter
                
                # Set up text object
                text_obj = c.beginText(50, height - 50)
                text_obj.setFont("Helvetica", 12)
                
                # Split content into lines
                lines = content.split('\n')
                
                for line in lines:
                    # Handle long lines by wrapping
                    if len(line) > 80:
                        words = line.split()
                        current_line = ""
                        for word in words:
                            if len(current_line + word) < 80:
                                current_line += word + " "
                            else:
                                text_obj.textLine(current_line.strip())
                                current_line = word + " "
                        if current_line:
                            text_obj.textLine(current_line.strip())
                    else:
                        text_obj.textLine(line)
                
                c.drawText(text_obj)
                c.save()
                
                messagebox.showinfo("Export PDF", f"Document exported to {filename}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Could not export to PDF: {str(e)}")
    
    def print_file(self):
        """Print current document"""
        try:
            if os.name == 'nt':  # Windows
                os.startfile(self.current_file, "print")
            else:
                messagebox.showinfo("Print", "Print functionality not available on this platform")
        except Exception as e:
            messagebox.showerror("Print Error", f"Could not print: {str(e)}")
    
    # Recent files management
    def load_recent_files(self):
        """Load recent files from JSON"""
        try:
            if os.path.exists(RECENT_FILES_FILE):
                with open(RECENT_FILES_FILE, 'r') as f:
                    self.recent_files = json.load(f)
            self.update_recent_menu()
        except Exception as e:
            print(f"Error loading recent files: {e}")
            self.recent_files = []
    
    def save_recent_files(self):
        """Save recent files to JSON"""
        try:
            with open(RECENT_FILES_FILE, 'w') as f:
                json.dump(self.recent_files, f)
        except Exception as e:
            print(f"Error saving recent files: {e}")
    
    def add_recent_file(self, filepath):
        """Add file to recent files list"""
        if filepath in self.recent_files:
            self.recent_files.remove(filepath)
        
        self.recent_files.insert(0, filepath)
        
        if len(self.recent_files) > MAX_RECENT:
            self.recent_files = self.recent_files[:MAX_RECENT]
        
        self.save_recent_files()
        self.update_recent_menu()
    
    def update_recent_menu(self):
        """Update recent files menu"""
        self.recent_menu.delete(0, 'end')
        
        if not self.recent_files:
            self.recent_menu.add_command(label="No recent files", state=DISABLED)
        else:
            for filepath in self.recent_files:
                if os.path.exists(filepath):
                    filename = os.path.basename(filepath)
                    self.recent_menu.add_command(
                        label=filename,
                        command=lambda f=filepath: self.open_file(f)
                    )
    
    # Auto-save functionality
    def start_auto_save(self):
        """Start auto-save timer"""
        if self.auto_save_var.get():
            self.auto_save_timer()
    
    def auto_save_timer(self):
        """Auto-save timer function"""
        if self.auto_save_var.get() and self.is_modified and self.current_file:
            self.save_file()
        
        # Schedule next auto-save
        if self.auto_save_var.get():
            self.window.after(AUTO_SAVE_INTERVAL * 1000, self.auto_save_timer)
    
    # Event handlers
    def on_text_change(self, event=None):
        """Handle text changes"""
        self.is_modified = True
        self.update_cursor_position()
        self.update_word_count()
        self.update_window_title()
    
    def on_key_release(self, event=None):
        """Handle key release events"""
        self.highlight_syntax()
    
    def on_mouse_wheel(self, event):
        """Handle mouse wheel for zoom"""
        if event.state & 0x4:  # Ctrl key pressed
            if event.delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            return "break"
    
    def highlight_syntax(self):
        """Basic syntax highlighting for Python files"""
        if not self.current_file or not self.current_file.endswith('.py'):
            return
        
        content = self.text_area.get(1.0, END)
        
        # Clear existing tags
        self.text_area.tag_remove('keyword', 1.0, END)
        self.text_area.tag_remove('string', 1.0, END)
        self.text_area.tag_remove('comment', 1.0, END)
        
        # Python keywords
        keywords = ['def', 'class', 'if', 'elif', 'else', 'for', 'while', 'try', 'except', 'finally',
                   'import', 'from', 'as', 'return', 'yield', 'lambda', 'with', 'assert', 'break',
                   'continue', 'pass', 'raise', 'and', 'or', 'not', 'in', 'is', 'True', 'False', 'None']
        
        # Highlight keywords
        for keyword in keywords:
            start = '1.0'
            while True:
                pos = self.text_area.search(r'\b' + keyword + r'\b', start, stopindex=END, regexp=True)
                if not pos:
                    break
                end = f"{pos}+{len(keyword)}c"
                self.text_area.tag_add('keyword', pos, end)
                start = end
        
        # Configure tags
        self.text_area.tag_config('keyword', foreground='blue')
        self.text_area.tag_config('string', foreground='green')
        self.text_area.tag_config('comment', foreground='gray')
    
    # Status and UI updates
    def update_status(self, message):
        """Update status bar"""
        self.status_bar.config(text=message)
        self.window.after(3000, lambda: self.status_bar.config(text="Ready"))
    
    def update_cursor_position(self):
        """Update cursor position in status bar"""
        try:
            line, col = self.text_area.index(INSERT).split('.')
            self.cursor_position.config(text=f"Ln {line}, Col {col}")
        except:
            self.cursor_position.config(text="Ln 1, Col 1")
    
    def update_word_count(self):
        """Update word count in status bar"""
        try:
            content = self.text_area.get(1.0, END)
            words = len(content.split())
            self.word_count.config(text=f"Words: {words}")
        except:
            self.word_count.config(text="Words: 0")
    
    def update_window_title(self):
        """Update window title"""
        if self.current_file:
            filename = os.path.basename(self.current_file)
            if self.is_modified:
                self.window.title(f"{APP_NAME} - {filename} *")
            else:
                self.window.title(f"{APP_NAME} - {filename}")
        else:
            if self.is_modified:
                self.window.title(f"{APP_NAME} - Untitled *")
            else:
                self.window.title(f"{APP_NAME} - Untitled")
    
    # Preferences and settings
    def show_preferences(self):
        """Show preferences dialog"""
        prefs_window = Toplevel(self.window)
        prefs_window.title("Preferences")
        prefs_window.geometry("400x300")
        prefs_window.resizable(False, False)
        
        # Editor preferences
        editor_frame = ttk.LabelFrame(prefs_window, text="Editor Settings", padding=10)
        editor_frame.pack(fill=X, padx=10, pady=5)
        
        # Font settings
        font_frame = Frame(editor_frame)
        font_frame.pack(fill=X, pady=5)
        
        Label(font_frame, text="Font:").pack(side=LEFT)
        font_combo = ttk.Combobox(font_frame, textvariable=self.font_name, 
                                 values=sorted(font.families()), width=15)
        font_combo.pack(side=LEFT, padx=5)
        
        Label(font_frame, text="Size:").pack(side=LEFT, padx=(10, 0))
        size_spin = Spinbox(font_frame, from_=8, to=72, width=5, textvariable=self.font_size)
        size_spin.pack(side=LEFT, padx=5)
        
        # Editor options
        Checkbutton(editor_frame, text="Word Wrap", variable=self.word_wrap_var).pack(anchor=W, pady=2)
        Checkbutton(editor_frame, text="Show Line Numbers", variable=self.line_numbers_var).pack(anchor=W, pady=2)
        Checkbutton(editor_frame, text="Auto Save", variable=self.auto_save_var).pack(anchor=W, pady=2)
        
        # Theme settings
        theme_frame = ttk.LabelFrame(prefs_window, text="Theme", padding=10)
        theme_frame.pack(fill=X, padx=10, pady=5)
        
        Radiobutton(theme_frame, text="Light", variable=self.theme_var, value="light").pack(anchor=W)
        Radiobutton(theme_frame, text="Dark", variable=self.theme_var, value="dark").pack(anchor=W)
        
        # Buttons
        button_frame = Frame(prefs_window)
        button_frame.pack(fill=X, padx=10, pady=10)
        
        def apply_preferences():
            self.change_font()
            self.toggle_word_wrap()
            self.toggle_line_numbers()
            if self.theme_var.get() == 'dark':
                self.apply_dark_theme()
            else:
                self.apply_light_theme()
            self.save_settings()
            prefs_window.destroy()
        
        Button(button_frame, text="Apply", command=apply_preferences).pack(side=RIGHT, padx=5)
        Button(button_frame, text="Cancel", command=prefs_window.destroy).pack(side=RIGHT)
    
    def load_settings(self):
        """Load settings from config"""
        try:
            # Apply theme
            if self.theme_var.get() == 'dark':
                self.apply_dark_theme()
            else:
                self.apply_light_theme()
            
            # Apply font
            self.change_font()
            
            # Apply word wrap
            self.toggle_word_wrap()
            
            # Apply line numbers
            self.toggle_line_numbers()
            
        except Exception as e:
            print(f"Error loading settings: {e}")
    
    def save_settings(self):
        """Save current settings to config"""
        try:
            self.config_manager.set('EDITOR', 'font_name', self.font_name.get())
            self.config_manager.set('EDITOR', 'font_size', self.font_size.get())
            self.config_manager.set('EDITOR', 'theme', self.theme_var.get())
            self.config_manager.set('EDITOR', 'word_wrap', str(self.word_wrap_var.get()))
            self.config_manager.set('EDITOR', 'line_numbers', str(self.line_numbers_var.get()))
            self.config_manager.set('EDITOR', 'auto_save', str(self.auto_save_var.get()))
            
            # Save window geometry
            geometry = self.window.geometry()
            width, height = geometry.split('+')[0].split('x')
            self.config_manager.set('APPEARANCE', 'window_width', width)
            self.config_manager.set('APPEARANCE', 'window_height', height)
            
            self.config_manager.save_config()
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    # Help and about
    def show_shortcuts(self):
        """Show keyboard shortcuts"""
        shortcuts_text = """
Keyboard Shortcuts:

File Operations:
Ctrl+N - New File
Ctrl+O - Open File
Ctrl+S - Save File
Ctrl+Shift+S - Save As
Ctrl+Q - Exit
Ctrl+P - Print

Edit Operations:
Ctrl+Z - Undo
Ctrl+Y - Redo
Ctrl+X - Cut
Ctrl+C - Copy
Ctrl+V - Paste
Ctrl+A - Select All
Ctrl+F - Find & Replace
Ctrl+G - Go to Line

View Operations:
Ctrl++ - Zoom In
Ctrl+- - Zoom Out
Ctrl+0 - Reset Zoom
        """
        
        messagebox.showinfo("Keyboard Shortcuts", shortcuts_text)
    
    def show_about(self):
        """Show about dialog"""
        about_text = f"""
{APP_NAME} v{APP_VERSION}

A full-featured text editor built with Python and Tkinter.

Features:
• Syntax highlighting
• Find & replace
• Auto-save
• Recent files
• Export to PDF
• Multiple themes
• Line numbers
• Word wrap
• Spell check (if available)
• Drag & drop support

Built with Python {sys.version.split()[0]}
        """
        
        messagebox.showinfo("About", about_text)
    
    def on_closing(self):
        """Handle window closing"""
        if self.is_modified:
            if not self.ask_save_changes():
                return
        
        self.save_settings()
        self.window.destroy()
    
    def run(self):
        """Run the application"""
        self.window.mainloop()

# Main entry point
if __name__ == "__main__":
    try:
        app = TextEditor()
        app.run()
    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()