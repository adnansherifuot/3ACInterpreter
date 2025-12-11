import json
import re
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox

from stack_frame import StackFrame
from view import AppView
from vm import VM


class AppController:
    """The Controller class, handling all application logic and state."""
    def __init__(self, master):
        self.master = master
        master.title("3AC Interpreter")
        master.geometry("1200x800")

        self.vm = VM(console_output_widget=None)
        self.view = AppView(master, self)

        # Link VM console to the view's widget
        self.vm.console_output = self.view.console_text

        self.current_3ac_lines = []
        self.breakpoints = set()
        self.watch_window = None
        self.watched_variables = []
        
        # --- Search state ---
        self.search_window = None
        self.search_entry = None

        # Bind keyboard shortcuts
        self.master.bind_all("<F5>", self.run_execution)
        self.master.bind_all("<F10>", self.step_execution)

        self._load_config()

    def update_status_bar(self, event=None):
        """Updates the status bar with the current line and column number."""
        # The widget is disabled, so we can't get the INSERT mark directly.
        # We get the position from the event if available, otherwise default.
        try:
            row, col = self.view.code_display.index(f"@{event.x},{event.y}").split('.')
            self.view.status_bar.config(text=f"Line: {row}, Col: {col}")
        except: # Fallback for cases without an event
            row, col = self.view.code_display.index(tk.INSERT).split('.')
            self.view.status_bar.config(text=f"Line: {row}, Col: {col}")

    def exit_app(self):
        """Closes the application."""
        self._save_config()
        self.master.quit()

    def _save_config(self):
        """Saves UI configuration like pane positions to a file."""
        try:
            config = {
                'main_pane_sash_pos': self.view.main_pane.sash_coord(0)[0],
                'right_pane_sash_pos': [self.view.right_pane.sash_coord(i)[1] for i in
                                        range(len(self.view.right_pane.panes()) - 1)]
            }
            with open('config.json', 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Could not save config: {e}") # Log to console, but don't block exit

    def _load_config(self):
        """Loads UI configuration from a file and applies it."""
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)

            # We need to wait until the window is drawn to apply sash positions
            def apply_sash_positions():
                if config.get('main_pane_sash_pos'):
                    self.view.main_pane.sash_place(0, config['main_pane_sash_pos'], 0)
                
                right_pane_sashes = config.get('right_pane_sash_pos', [])
                for i, pos_y in enumerate(right_pane_sashes):
                    if i < (len(self.view.right_pane.panes()) - 1):
                        self.view.right_pane.sash_place(i, 0, pos_y)

            self.master.after(100, apply_sash_positions)
        except (FileNotFoundError, json.JSONDecodeError):
            pass # No config file or it's invalid, just start with defaults

    def clear_console(self):
        """Clears the VM console output widget."""
        if self.view.console_text:
            self.view.console_text.delete('1.0', tk.END)
            self.view.console_text.insert(tk.END, "--- VM Console Cleared ---\n")

    def load_file(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("3AC Files", "*.3ac"), ("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if not filepath:
            return

        try:
            with open(filepath, 'r') as f:
                self.current_3ac_lines = f.readlines()

            self.vm.load_program(self.current_3ac_lines)
            self.breakpoints.clear()
            self.watched_variables.clear()
            self._update_code_display()
            self.update_displays()
            messagebox.showinfo("Load 3AC", f"Successfully loaded {filepath}")
        except Exception as e:
            messagebox.showerror("Error Loading File", f"Could not load 3AC file: {e}")
            self.current_3ac_lines = []
            self.vm.reset_state()
            self._update_code_display()  # Clear code display on error
            self.update_displays()

    def show_about(self):
        """Displays an about message box."""
        messagebox.showinfo(
            "About",
            "3AC Interpreter v1.0\n\n"
            "A virtual machine and debugger for a custom 3-Address Code language.\n\n"
            "Developed to demonstrate interpreter design and execution flow."
        )

    def show_help(self):
        """Creates and shows a help window with usage and syntax information."""
        help_window = tk.Toplevel(self.view.master)
        help_window.title("Help")
        help_window.geometry("700x600")

        help_text_widget = scrolledtext.ScrolledText(help_window, wrap=tk.WORD, font=("Consolas", 10), padx=10, pady=10)
        help_text_widget.pack(fill=tk.BOTH, expand=True)

        usage_guide = """
--- How to Use the Interpreter ---

1.  **Load 3AC File**: Click this button to open a `.3ac` or `.txt` file containing your 3-Address Code. The code will appear in the "3AC Source Code" panel.

2.  **Run**: Executes the program from the current position until it halts, finishes, or hits a breakpoint.

3.  **Step**: Executes only the single, currently highlighted instruction. This allows you to trace the program's execution line by line.

4.  **Reset**: Resets the virtual machine to its initial state, clearing all memory and resetting the program counter to the beginning. The loaded code remains.

5.  **Breakpoints**: Click on a line number in the source code panel to set or remove a breakpoint (highlighted in red). The "Run" command will pause execution when it reaches a breakpoint.

6.  **Watch Window**: Click "Watch" to open a window where you can monitor the values of specific variables as the program runs.

"""

        syntax_guide = """
--- 3AC Syntax Specification ---

"""
        help_text_widget.insert(tk.END, usage_guide)
        help_text_widget.insert(tk.END, syntax_guide)
        help_text_widget.insert(tk.END, open('c:\\Users\\adnan\\OneDrive - University of Tripoli\\قسم الحاسب الآلي\\المواد\\CS432\\My3ACInterpreter\\3ACInterpreter\\3AC Syntax for interpreter.txt').read())
        help_text_widget.config(state=tk.DISABLED)  # Make it read-only

    def export_vm_state(self):
        """Exports the current state of the VM to a JSON file."""
        if not self.current_3ac_lines:
            messagebox.showwarning("Export State", "No program is loaded to export its state.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Save VM State As"
        )
        if not filepath:
            return

        try:
            # Create a serializable representation of the call stack
            serializable_stack = []
            for frame in self.vm.call_stack:
                serializable_stack.append({
                    "func_name": frame.func_name,
                    "return_address": frame.return_address,
                    "return_var_name": frame.return_var_name,
                    "locals": frame.locals,
                    "params": frame.params
                })

            # Create a dictionary of only the active heap slots
            active_heap = {i: v for i, v in enumerate(self.vm.heap) if v is not None}

            vm_state = {
                "pc": self.vm.pc,
                "global_memory": self.vm.global_memory,
                "call_stack": serializable_stack,
                "heap": active_heap
            }

            with open(filepath, 'w') as f:
                json.dump(vm_state, f, indent=4)
            messagebox.showinfo("Export Successful", f"VM state successfully exported to {filepath}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export VM state: {e}")

    def import_vm_state(self):
        """Imports a previously exported VM state from a JSON file."""
        if not self.current_3ac_lines:
            messagebox.showwarning("Import State", "A 3AC program must be loaded before importing a state.")
            return

        filepath = filedialog.askopenfilename(
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
            title="Select VM State File to Import"
        )
        if not filepath:
            return

        try:
            with open(filepath, 'r') as f:
                vm_state = json.load(f)

            # --- Restore VM State ---
            self.vm.pc = vm_state['pc']
            self.vm.global_memory = vm_state['global_memory']

            # Reconstruct the call stack from serialized data
            self.vm.call_stack = []
            for frame_data in vm_state['call_stack']:
                frame = StackFrame(frame_data['func_name'], frame_data['return_address'], frame_data['return_var_name'])
                frame.locals = frame_data['locals']
                frame.params = frame_data['params']
                self.vm.call_stack.append(frame)

            # Reconstruct the heap
            self.vm.heap = [None] * len(self.vm.heap) # Reset heap to its default size
            active_heap_from_file = vm_state['heap']
            for addr_str, value in active_heap_from_file.items():
                addr = int(addr_str)
                if 0 <= addr < len(self.vm.heap):
                    self.vm.heap[addr] = value
            
            # Reconstruct the free list
            self.vm.free_heap_slots = [i for i, v in enumerate(self.vm.heap) if v is None]

            self.update_displays()
            messagebox.showinfo("Import Successful", f"VM state successfully imported from {filepath}")
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to import VM state: {e}")

    def show_search_dialog(self):
        """Creates and shows the search dialog window."""
        if self.search_window and self.search_window.winfo_exists():
            self.search_window.lift()
            return

        self.search_window = tk.Toplevel(self.view.master)
        self.search_window.title("Search")
        self.search_window.geometry("300x60")
        self.search_window.resizable(False, False)
        self.search_window.transient(self.view.master) # Keep it on top of the main window

        search_frame = tk.Frame(self.search_window, padx=5, pady=5)
        search_frame.pack(fill=tk.X, expand=True)

        tk.Label(search_frame, text="Find:").pack(side=tk.LEFT)
        self.search_entry = tk.Entry(search_frame)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.search_entry.focus_set()
        self.search_entry.bind("<Return>", self.find_next)

        button_frame = tk.Frame(self.search_window)
        button_frame.pack(fill=tk.X, expand=True, padx=5)
        tk.Button(button_frame, text="Find Next", command=self.find_next).pack(side=tk.LEFT, expand=True, fill=tk.X)
        tk.Button(button_frame, text="Find Prev", command=self.find_previous).pack(side=tk.LEFT, expand=True, fill=tk.X)

        # When the search window is closed, clear the highlight
        self.search_window.protocol("WM_DELETE_WINDOW", self._on_search_close)

    def _on_search_close(self):
        """Handles the closing of the search window."""
        self.view.code_display.tag_remove("highlight", "1.0", tk.END)
        self.search_window.destroy()
        self.search_window = None

    def _perform_search(self, forward=True):
        """The core search logic."""
        if not self.search_entry: return
        
        search_term = self.search_entry.get()
        if not search_term: return

        self.view.code_display.tag_remove("highlight", "1.0", tk.END)
        
        start_pos = self.view.code_display.index(tk.INSERT)
        if not forward:
            # For reverse search, start from just before the current cursor
            start_pos = f"{start_pos}-1c"

        pos = self.view.code_display.search(search_term, start_pos, backwards=(not forward), nocase=True, stopindex=None)

        if pos:
            end_pos = f"{pos}+{len(search_term)}c"
            self.view.code_display.tag_add("highlight", pos, end_pos)
            self.view.code_display.see(pos)
            self.view.code_display.mark_set(tk.INSERT, pos) # Move cursor to the found text
        else:
            messagebox.showinfo("Search", f"No more occurrences of '{search_term}' found.")

    def find_next(self, event=None):
        self._perform_search(forward=True)

    def find_previous(self, event=None):
        self._perform_search(forward=False)

    def toggle_watch_window(self):
        """Creates or focuses the variable watch window."""
        if self.watch_window and self.watch_window.winfo_exists():
            self.watch_window.lift()
            return

        self.watch_window = tk.Toplevel(self.view.master)
        self.watch_window.title("Watch Variables")
        self.watch_window.geometry("350x400")

        # --- Input Frame ---
        input_frame = tk.Frame(self.watch_window, padx=5, pady=5)
        input_frame.pack(side=tk.TOP, fill=tk.X)

        tk.Label(input_frame, text="Variable:").pack(side=tk.LEFT)
        self.watch_entry = tk.Entry(input_frame, font=("Consolas", 10))
        self.watch_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.watch_entry.bind("<Return>", self.add_watch_variable) # Allow adding with Enter key
        add_button = tk.Button(input_frame, text="Add", command=self.add_watch_variable)
        add_button.pack(side=tk.LEFT)

        # --- Display Frame ---
        display_frame = tk.Frame(self.watch_window, padx=5, pady=5)
        display_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        # Use a Listbox for selectable items
        scrollbar = tk.Scrollbar(display_frame, orient=tk.VERTICAL)
        self.view.watch_display = tk.Listbox(display_frame, font=("Consolas", 10), yscrollcommand=scrollbar.set, exportselection=False)
        scrollbar.config(command=self.view.watch_display.yview)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.view.watch_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # --- Remove Button ---
        remove_button = tk.Button(self.watch_window, text="Remove Selected Variable", command=self.remove_watch_variable)
        remove_button.pack(side=tk.BOTTOM, pady=5)
        
        self.update_watch_display() # Initial population

    def add_watch_variable(self, event=None):
        """Adds a variable from the entry to the watch list."""
        var_name = self.watch_entry.get().strip()
        if var_name and var_name not in self.watched_variables:
            self.watched_variables.append(var_name)
            self.watch_entry.delete(0, tk.END)
            self.update_displays() # Update all displays to show new variable

    def remove_watch_variable(self):
        """Removes the selected variable from the watch list."""
        selected_indices = self.view.watch_display.curselection()
        if not selected_indices:
            messagebox.showwarning("Remove Watch", "Please select a variable to remove.")
            return

        # Get the full text of the selected item (e.g., "my_var = 123")
        selected_text = self.view.watch_display.get(selected_indices[0])
        # Extract just the variable name
        var_name_to_remove = selected_text.split(' = ')[0]
        self.watched_variables.remove(var_name_to_remove)
        self.update_displays()

    def toggle_breakpoint(self, event):
        """Toggles a breakpoint on the clicked line."""
        # The text widget is disabled, so we need to enable it briefly to manage tags
        self.view.code_display.config(state=tk.NORMAL)

        # Get the line number from the click position
        index = self.view.code_display.index(f"@{event.x},{event.y}")
        line_num = int(index.split('.')[0]) - 1  # Convert to 0-based index

        if line_num in self.breakpoints:
            self.breakpoints.remove(line_num)
            self.view.code_display.tag_remove("breakpoint", f"{line_num + 1}.0", f"{line_num + 1}.end")
        else:
            self.breakpoints.add(line_num)
            self.view.code_display.tag_add("breakpoint", f"{line_num + 1}.0", f"{line_num + 1}.end")

        self.view.code_display.config(state=tk.DISABLED)
        self.update_status_bar(event) # Update status bar after click

    def _update_code_display(self):
        self.view.code_display.config(state=tk.NORMAL)
        self.view.code_display.delete('1.0', tk.END)

        # Display line numbers and highlighted code
        for i, line in enumerate(self.current_3ac_lines):
            line_num_str = f"{i:4d}: "
            line_start_index = f"{i + 1}.0"
            self.view.code_display.insert(tk.END, line_num_str)
            self._highlight_syntax(line.strip(), line_start_index, len(line_num_str))
            self.view.code_display.insert(tk.END, "\n")

        # Re-apply breakpoint tags
        for bp_line in self.breakpoints:
            self.view.code_display.tag_add("breakpoint", f"{bp_line + 1}.0", f"{bp_line + 1}.end")

        # Remove current line highlight before re-applying
        self.view.code_display.tag_remove("current_line", "1.0", tk.END)

        # Highlight current instruction if running
        if self.vm.running and not self.vm.halted and 0 <= self.vm.pc < len(self.vm.program):
            # Find the actual line number in the original file for the current instruction
            original_line_num = self.vm.program[self.vm.pc].line_num
            start_index = f"{original_line_num + 1}.0"
            end_index = f"{original_line_num + 1}.end"
            self.view.code_display.tag_add("current_line", start_index, end_index)
            self.view.code_display.see(start_index)  # Scroll to the current line

        self.view.code_display.config(state=tk.DISABLED)

    def _highlight_syntax(self, line, line_start_index, content_start_offset):
        """Applies syntax highlighting tags to a single line of code."""
        if not line or line.startswith('#'):
            start = f"{line_start_index}+{content_start_offset}c"
            self.view.code_display.insert(start, line)
            self.view.code_display.tag_add("comment", start, f"{start}+{len(line)}c")
            return

        if line.endswith(':'):
            start = f"{line_start_index}+{content_start_offset}c"
            self.view.code_display.insert(start, line)
            self.view.code_display.tag_add("label", start, f"{start}+{len(line)}c")
            return

        match = re.match(r'(\w+)\s*(.*)', line)
        if not match:
            start = f"{line_start_index}+{content_start_offset}c"
            self.view.code_display.insert(start, line) # Insert plain if no match
            return

        opcode, operands_str = match.groups()
        
        # Insert and highlight opcode
        opcode_start = f"{line_start_index}+{content_start_offset}c"
        self.view.code_display.insert(opcode_start, opcode)
        self.view.code_display.tag_add("opcode", opcode_start, f"{opcode_start}+{len(opcode)}c")

        # Insert and highlight operands
        current_pos = len(opcode)
        # Use a more robust regex for splitting operands, handling strings with commas
        operands_and_delimiters = re.split(r'(,"[^"]*"|,\s*)', " " + operands_str)
        
        for part in operands_and_delimiters:
            if not part: continue
            part_start_index = f"{opcode_start}+{current_pos}c"
            self.view.code_display.insert(part_start_index, part)
            
            # Check if the part (trimmed) is a literal
            if self.vm._parse_operand_value(part.strip().strip(',')) != part.strip().strip(','):
                self.view.code_display.tag_add("literal", part_start_index, f"{part_start_index}+{len(part)}c")
            current_pos += len(part)

    def update_displays(self):
        self._update_code_display()
        self.update_watch_display()

        # Update Memory Display
        self.view.mem_display.config(state=tk.NORMAL)
        self.view.mem_display.delete('1.0', tk.END)
        self.view.mem_display.insert(tk.END, "--- Global Memory ---\n")
        if not self.vm.global_memory:
            self.view.mem_display.insert(tk.END, "(empty)\n")
        else:
            for k, v in self.vm.global_memory.items():
                self.view.mem_display.insert(tk.END, f"{k} = {repr(v)}\n")

        if self.vm.call_stack:
            current_frame = self.vm.call_stack[-1]
            self.view.mem_display.insert(tk.END, "\n--- Current Stack Frame (Locals) ---\n")
            if not current_frame.locals and not current_frame.params:
                self.view.mem_display.insert(tk.END, "(empty)\n")
            else:
                if current_frame.params:
                    self.view.mem_display.insert(tk.END, "Parameters:\n")
                    for k, v in current_frame.params.items():
                        self.view.mem_display.insert(tk.END, f"  {k} = {repr(v)}\n")
                if current_frame.locals:
                    self.view.mem_display.insert(tk.END, "Local Variables:\n")
                    for k, v in current_frame.locals.items():
                        self.view.mem_display.insert(tk.END, f"  {k} = {repr(v)}\n")
        self.view.mem_display.config(state=tk.DISABLED)

        # Update Heap Display
        self.view.heap_display.config(state=tk.NORMAL)
        self.view.heap_display.delete('1.0', tk.END)
        self.view.heap_display.insert(tk.END, "--- Heap Memory (Address: Value) ---\n")
        active_heap_slots = {i: v for i, v in enumerate(self.vm.heap) if
                             v is not None or i not in self.vm.free_heap_slots}
        if not active_heap_slots:
            self.view.heap_display.insert(tk.END, "(empty / all free)\n")
        else:
            for addr in sorted(active_heap_slots.keys()):
                val = self.vm.heap[addr]
                self.view.heap_display.insert(tk.END, f"[{addr:04d}]: {repr(val)}\n")
        self.view.heap_display.config(state=tk.DISABLED)

        # Update Stack Display
        self.view.stack_display.config(state=tk.NORMAL)
        self.view.stack_display.delete('1.0', tk.END)
        self.view.stack_display.insert(tk.END, "--- Call Stack (Top -> Bottom) ---\n")
        if not self.vm.call_stack:
            self.view.stack_display.insert(tk.END, "(empty)\n")
        else:
            for i, frame in enumerate(reversed(self.vm.call_stack)):  # Display top of stack first
                self.view.stack_display.insert(tk.END,
                                          f"[{len(self.vm.call_stack) - 1 - i}] {frame.func_name} (ret_PC: {frame.return_address})\n")
        self.view.stack_display.config(state=tk.DISABLED)

    def update_watch_display(self):
        """Updates the content of the watch window."""
        if not self.watch_window or not self.watch_window.winfo_exists() or not hasattr(self.view, 'watch_display'):
            return

        self.view.watch_display.delete(0, tk.END) # Clear the listbox

        if not self.watched_variables:
            self.view.watch_display.insert(tk.END, "(No variables to watch)")
        else:
            for var_name in self.watched_variables:
                value = self.vm._get_operand_value(var_name)
                self.view.watch_display.insert(tk.END, f"{var_name} = {repr(value)}")

    def step_execution(self, event=None):
        if self.vm.running:
            try:
                stepped = self.vm.step()
                if not stepped:  # Program halted or finished
                    messagebox.showinfo("Execution Complete", "Program execution finished or halted.")
                self.update_displays()
            except Exception as e:
                # Error is already logged to console by VM, and message box shown.
                self.update_displays()  # Update to show state at error
        else:
            messagebox.showwarning("Execution Status", "Program is not running (either not loaded, halted, or finished).")

    def run_execution(self, event=None):
        """Runs the program until a breakpoint is hit or it halts."""
        if not self.vm.running:
            messagebox.showwarning("Execution Status", "Program is not running. Please load a file or reset.")
            return

        try:
            # Loop until the program stops for a reason (halt, error, breakpoint)
            while self.vm.running:
                # Check for breakpoint BEFORE executing the instruction
                current_instr = self.vm.program[self.vm.pc]
                if current_instr.line_num in self.breakpoints:
                    messagebox.showinfo("Breakpoint Hit", f"Execution paused at line {current_instr.line_num + 1}.")
                    self.update_displays()
                    return  # Stop running but keep the program active

                stepped = self.vm.step()
                if not stepped:  # Program halted or finished naturally
                    messagebox.showinfo("Execution Complete", "Program execution finished or halted.")
                    break  # Exit the while loop

            self.update_displays()  # Final update
        except Exception as e:
            # This will catch any unexpected errors during the run loop
            self.update_displays()

    def reset_execution(self):
        if self.current_3ac_lines:
            try:
                self.breakpoints.clear()
                self.watched_variables.clear()
                self.vm.load_program(self.current_3ac_lines)
                self.update_displays()
                messagebox.showinfo("Reset", "Program reset to beginning.")
            except Exception as e:
                messagebox.showerror("Reset Error", f"Error resetting program: {e}")
                self.current_3ac_lines = []  # Clear program on load error during reset
                self.vm.reset_state()
                self._update_code_display()
                self.update_displays()
        else:
            messagebox.showinfo("Reset", "No program loaded to reset.")

    def run(self):
        self.master.mainloop()