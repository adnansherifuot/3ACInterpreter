import tkinter as tk
from tkinter import scrolledtext


class AppView:
    """The View class, responsible for creating and managing all GUI widgets."""
    def __init__(self, master, controller):
        self.master = master
        self.controller = controller
        self._create_widgets()

        # Configure tags for highlighting
        self.code_display.tag_configure("breakpoint", background="#ff8a82", foreground="black")
        self.code_display.tag_configure("highlight", background="yellow")
        self.code_display.tag_configure("current_line", background="lightblue", foreground="black")

        # Tags for syntax highlighting
        bold_font = ("Consolas", 10, "bold")
        self.code_display.tag_configure("opcode", foreground="#0000ff", font=bold_font) # Blue
        self.code_display.tag_configure("literal", foreground="#d9534f") # Red
        self.code_display.tag_configure("label", foreground="#c58300", font=bold_font) # Orange-ish
        self.code_display.tag_configure("comment", foreground="#5cb85c", font=("Consolas", 10, "italic")) # Green

    def _create_widgets(self):
        # --- Menu Bar ---
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)

        # File Menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load 3AC File...", command=self.controller.load_file)
        file_menu.add_separator()
        file_menu.add_command(label="Import VM State...", command=self.controller.import_vm_state)
        file_menu.add_command(label="Export VM State...", command=self.controller.export_vm_state)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.controller.exit_app)

        # Execution Menu
        exec_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Execution", menu=exec_menu)
        exec_menu.add_command(label="Run", command=self.controller.run_execution, accelerator="F5")
        exec_menu.add_command(label="Step", command=self.controller.step_execution, accelerator="F10")
        exec_menu.add_command(label="Reset", command=self.controller.reset_execution)
        exec_menu.add_separator()
        exec_menu.add_command(label="Clear Console", command=self.controller.clear_console)
        exec_menu.add_separator()
        exec_menu.add_command(label="Search Code...", command=self.controller.show_search_dialog)

        # View Menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Watch Variables", command=self.controller.toggle_watch_window)

        # Help Menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="View Help", command=self.controller.show_help)
        help_menu.add_command(label="About", command=self.controller.show_about)

        # --- Main Content Area ---
        self.main_pane = tk.PanedWindow(self.master, orient=tk.HORIZONTAL, sashrelief=tk.RAISED)
        self.main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Left Pane: 3AC Code Display ---
        code_frame = tk.LabelFrame(self.main_pane, text="3AC Source Code", padx=5, pady=5)
        self.main_pane.add(code_frame, width=400)  # Initial width

        self.code_display = scrolledtext.ScrolledText(code_frame, wrap=tk.NONE, font=("Consolas", 10))
        self.code_display.pack(fill=tk.BOTH, expand=True)
        self.code_display.config(state=tk.DISABLED)  # Make it read-only
        self.code_display.bind("<Button-1>", self.controller.toggle_breakpoint)
        self.code_display.bind("<KeyRelease>", self.controller.update_status_bar)
        self.code_display.bind("<ButtonRelease-1>", self.controller.update_status_bar)

        self.status_bar = tk.Label(self.master, text="Line: 1, Col: 0", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # --- Right Pane: Memory, Stack, Console ---
        self.right_pane = tk.PanedWindow(self.main_pane, orient=tk.VERTICAL, sashrelief=tk.RAISED)
        self.main_pane.add(self.right_pane)

        # Global/Local Memory Display
        mem_frame = tk.LabelFrame(self.right_pane, text="Memory (Global / Current Local)", padx=5, pady=5)
        self.right_pane.add(mem_frame, height=200)  # Initial height
        self.mem_display = scrolledtext.ScrolledText(mem_frame, wrap=tk.WORD, font=("Consolas", 9))
        self.mem_display.pack(fill=tk.BOTH, expand=True)
        self.mem_display.config(state=tk.DISABLED)

        # Heap Memory Display
        heap_frame = tk.LabelFrame(self.right_pane, text="Heap Memory", padx=5, pady=5)
        self.right_pane.add(heap_frame, height=200)
        self.heap_display = scrolledtext.ScrolledText(heap_frame, wrap=tk.WORD, font=("Consolas", 9))
        self.heap_display.pack(fill=tk.BOTH, expand=True)
        self.heap_display.config(state=tk.DISABLED)

        # Stack Display
        stack_frame = tk.LabelFrame(self.right_pane, text="Call Stack", padx=5, pady=5)
        self.right_pane.add(stack_frame, height=150)
        self.stack_display = scrolledtext.ScrolledText(stack_frame, wrap=tk.WORD, font=("Consolas", 9))
        self.stack_display.pack(fill=tk.BOTH, expand=True)
        self.stack_display.config(state=tk.DISABLED)

        # Console Output
        console_frame = tk.LabelFrame(self.right_pane, text="Console Output", padx=5, pady=5)
        self.right_pane.add(console_frame, height=150)
        self.console_text = scrolledtext.ScrolledText(console_frame, wrap=tk.WORD, font=("Consolas", 9), bg="black",
                                                      fg="white")
        self.console_text.pack(fill=tk.BOTH, expand=True)
        self.console_text.config()  # Will be enabled by VM for writing