import re
import tkinter as tk
from tkinter import messagebox

from instruction import Instruction
from stack_frame import StackFrame


class VM:
    """
    Virtual Machine to execute 3-Address Code.
    Manages program counter, stack, global memory, and heap.
    """

    def __init__(self, console_output_widget=None):
        self.program = []  # List of Instruction objects
        self.labels = {}  # Map label name to instruction index
        self.pc = 0  # Program Counter
        self.global_memory = {}  # Global variables
        self.heap = []  # Heap for dynamic allocations (list of values)
        self.free_heap_slots = []  # Track free slots for simpler memory management (indices)
        self.call_stack = []  # Stack of StackFrame objects
        self.current_params = []  # Parameters for the next function call (before CALL instruction)
        self.running = False
        self.halted = False
        self.console_output = console_output_widget  # Tkinter widget for console output
        self.reset_state()

    def reset_state(self):
        """Resets the VM to its initial state."""
        self.pc = 0
        self.global_memory = {}
        self.heap = [None] * 100  # Pre-allocate some heap for simplicity, or grow dynamically
        self.free_heap_slots = list(range(len(self.heap)))  # All slots initially free
        self.call_stack = []
        self.current_params = []
        self.running = False
        self.halted = False
        if self.console_output:
            self.console_output.delete('1.0', tk.END)
            self.console_output.insert(tk.END, "--- VM Console ---\n")

        # Opcode dispatch table for refactored step method
        self.opcode_handlers = {
            'ASSIGN': self._handle_assignment, 'CONST_ASSIGN': self._handle_assignment,
            'ADD': self._handle_arithmetic, 'SUB': self._handle_arithmetic,
            'MUL': self._handle_arithmetic, 'DIV': self._handle_arithmetic,
            'MOD': self._handle_arithmetic, 'EQ': self._handle_arithmetic,
            'NE': self._handle_arithmetic, 'LT': self._handle_arithmetic,
            'LE': self._handle_arithmetic, 'GT': self._handle_arithmetic,
            'GE': self._handle_arithmetic, 'OR': self._handle_arithmetic,
            'AND': self._handle_arithmetic,
            'CONCAT': self._handle_string, 'STRLEN': self._handle_string,
            'GETCHAR': self._handle_string,
            'JUMP': self._handle_jump, 'JUMPT': self._handle_jump,
            'JUMPF': self._handle_jump,
            'PARAM': self._handle_function, 'REF_PARAM': self._handle_function,
            'CALL': self._handle_function, 'RETURN': self._handle_function,
            'PRINT': self._handle_misc, 'HALT': self._handle_misc,
            'UMINUS': self._handle_misc,
            'ALLOC_HEAP': self._handle_heap, 'FREE_HEAP': self._handle_heap,
            'ADDR_OF': self._handle_heap, 'DEREF_LOAD': self._handle_heap,
            'DEREF_STORE': self._handle_heap, 'INDEX_LOAD': self._handle_heap,
            'INDEX_STORE': self._handle_heap,
        }

    def _log_console(self, message):
        """Writes a message to the console output widget."""
        if self.console_output:
            self.console_output.insert(tk.END, message)
            self.console_output.see(tk.END)  # Scroll to end

    def load_program(self, tac_code_lines):
        """Parses 3AC code from lines and loads it into the VM."""
        self.reset_state()
        self.program = []
        self.labels = {}

        raw_instructions = []
        for i, line in enumerate(tac_code_lines):
            line = line.strip()
            if not line or line.startswith('#'):  # Ignore empty lines and comments
                continue

            # Check for label definition
            if line.endswith(':'):
                label_name = line[:-1]
                self.labels[label_name] = len(raw_instructions)  # Store PC for this label
                continue

            # Parse instruction: opcode, operands
            # Use regex to safely split opcode from the rest of the line, then split operands
            match = re.match(r'(\w+)\s*(.*)', line)
            if not match:
                raise ValueError(f"Syntax error at line {i + 1}: '{line}'")

            opcode = match.group(1).upper()  # Ensure opcode is uppercase
            operands_str = match.group(2).strip()

            operands = []
            if operands_str:
                # Split by comma, but be careful with strings that might contain commas if implemented
                # For now, assumes simple comma-separated variables/literals
                operands = [self._parse_operand_value(op.strip()) for op in operands_str.split(',')]

            raw_instructions.append(Instruction(opcode, *operands, line_num=i))

        self.program = raw_instructions  # Assign after all labels are processed

        # After loading all instructions, ensure labels in jumps are resolved
        # This pass is necessary because labels might be defined *after* they are used.
        for instr in self.program:
            # Handle special cases for labels in jumps
            if instr.opcode in ['JUMP', 'JUMPT', 'JUMPF']:
                target_label_name = instr.operands[0]  # The label name is the first operand
                if target_label_name not in self.labels:
                    raise ValueError(f"Undefined label '{target_label_name}' at 3AC line {instr.line_num}")
                instr.operands[0] = self.labels[target_label_name]  # Replace label name with target PC

        self.running = True

    def _parse_operand_value(self, op_str):
        """Attempts to convert operand string to int, float, bool, string literal, or keeps as variable name."""
        if op_str.lower() == 'true':
            return True
        if op_str.lower() == 'false':
            return False
        # Check for string literal first, as it might contain numbers
        if op_str.startswith('"') and op_str.endswith('"'):
            return op_str[1:-1]  # Return the string content without quotes
        if re.match(r"^-?\d+$", op_str):  # Integer
            return int(op_str)
        if re.match(r"^-?\d+\.\d*$", op_str):  # Float
            return float(op_str)
        return op_str  # Assume variable name

    def _get_operand_value(self, operand_name):
        """Retrieves the value of an operand from current scope or global memory."""
        if not isinstance(operand_name, str):
            return operand_name  # It's a literal value
        # Try current stack frame locals/params (top of the call stack)
        if self.call_stack:
            frame = self.call_stack[-1]
            if operand_name in frame.locals:
                val = frame.locals[operand_name]
                # This variable is not a parameter, so it's not a reference. Return its value.
                return val
            if operand_name in frame.params:
                param_info = frame.params[operand_name]
                # If param_info is a tuple, it's a reference pointer.
                # We dereference it here to get the value for the operation.
                if isinstance(param_info, tuple) and param_info[0] in ('heap', 'global', 'local'):
                    # This is a pass-by-reference parameter, so we get the value it points to.
                    return self._get_value_from_pointer(param_info)
                else:
                    # It's a pass-by-value parameter
                    return param_info

        # Try global memory
        if operand_name in self.global_memory:
            # Globals are not passed by reference in this model, so we just return the value.
            # If a global were passed by reference, its address would be in the current frame's params.
            return self.global_memory[operand_name]

        # If not found, it's either an error or an uninitialized variable.
        # For simplicity, we return None, but a production compiler would likely error here.
        # This allows us to handle `ADDR_OF` for uninitialized variables too.

        return None

    def _set_variable_value(self, var_name, value):
        """Sets the value of a variable in the current scope or global memory.
           Prioritizes local scope, then global."""
        if self.call_stack:
            frame = self.call_stack[-1]
            # Check if it's a local or a parameter being assigned to.
            if var_name in frame.locals or var_name.startswith('ARG'):
                frame.locals[var_name] = value
                return
            # If not in locals/params, it's a new local variable for the current frame
            frame.locals[var_name] = value
            return

        # If no call stack, it's a global variable
        self.global_memory[var_name] = value

    def _get_value_from_pointer(self, pointer):
        """Gets a value given a pointer tuple like ('heap', 123) or ('global', 'x')."""
        if not isinstance(pointer, tuple) or len(pointer) != 2:
            raise ValueError(f"Invalid pointer format: {pointer}")

        ptr_type, location = pointer
        if ptr_type == 'heap':
            if not (isinstance(location, int) and 0 <= location < len(self.heap)):
                raise ValueError(f"Invalid heap address in pointer: {pointer}")
            return self.heap[location]
        elif ptr_type == 'global':
            return self.global_memory.get(location)
        elif ptr_type == 'local':
            if not self.call_stack:
                raise RuntimeError("Attempted to access local pointer with no active stack frame.")
            return self.call_stack[-1].locals.get(location)
        else:
            raise TypeError(f"Unknown pointer type '{ptr_type}'")

    def _set_value_at_pointer(self, pointer, value):
        """Sets a value given a pointer tuple."""
        if not isinstance(pointer, tuple) or len(pointer) != 2:
            raise ValueError(f"Invalid pointer format for storing: {pointer}")

        ptr_type, location = pointer
        if ptr_type == 'heap':
            if not (isinstance(location, int) and 0 <= location < len(self.heap)):
                raise ValueError(f"Invalid heap address in pointer: {pointer}")
            self.heap[location] = value
        elif ptr_type == 'global':
            self.global_memory[location] = value
        elif ptr_type == 'local':
            if not self.call_stack:
                raise RuntimeError("Attempted to set local pointer value with no active stack frame.")
            self.call_stack[-1].locals[location] = value
        else:
            raise TypeError(f"Unknown pointer type '{ptr_type}'")

    def _get_variable_address(self, var_name):
        """
        Returns a 'pointer' tuple that describes the location of a variable.
        e.g., ('global', 'x'), ('local', 'y'), or ('heap', 123)
        """
        # Check if it's a local/param variable first
        if self.call_stack:
            frame = self.call_stack[-1]
            if var_name in frame.locals or var_name in frame.params:
                return ('local', var_name)
        # Check if it's a global variable
        if var_name in self.global_memory:
            return ('global', var_name)
        # If the variable doesn't exist, assume it will be a global one.
        return ('global', var_name)

    def _allocate_heap_slot(self):
        """Finds and returns a free heap address (index). Grows heap if needed."""
        if self.free_heap_slots:
            addr = self.free_heap_slots.pop(0)
            return addr

        # If no free slots, extend the heap dynamically
        current_heap_size = len(self.heap)
        self.heap.extend([None] * 50)  # Extend by 50 slots
        new_slots = list(range(current_heap_size, len(self.heap)))
        self.free_heap_slots.extend(new_slots)

        addr = self.free_heap_slots.pop(0)
        return addr

    def _free_heap_slot(self, addr):
        """Marks a heap address as free. (Simple approach, not full GC)"""
        if isinstance(addr, int) and 0 <= addr < len(self.heap):
            if self.heap[addr] is not None:  # Only clear if it held a value
                self.heap[addr] = None  # Clear value
            if addr not in self.free_heap_slots:  # Avoid duplicates if already free
                self.free_heap_slots.append(addr)
        else:
            self._log_console(f"Warning: Attempted to free invalid or out-of-bounds heap address {addr}\n")

    def _handle_assignment(self, instr):
        opcode, operands = instr.opcode, instr.operands
        if opcode == 'ASSIGN':
            target, source = operands
            value = self._get_operand_value(source)
            self._set_variable_value(target, value)
        elif opcode == 'CONST_ASSIGN':
            target, value = operands
            self._set_variable_value(target, value)
        self.pc += 1

    def _handle_arithmetic(self, instr):
        opcode, operands = instr.opcode, instr.operands
        target, op1_name, op2_name = operands
        val1 = self._get_operand_value(op1_name)
        val2 = self._get_operand_value(op2_name)

        result = None
        if opcode == 'ADD': result = val1 + val2
        elif opcode == 'SUB': result = val1 - val2
        elif opcode == 'MUL': result = val1 * val2
        elif opcode == 'DIV':
            if val2 == 0: raise ZeroDivisionError("Division by zero")
            result = val1 / val2
        elif opcode == 'MOD':
            if val2 == 0: raise ZeroDivisionError("Modulo by zero")
            result = val1 % val2
        elif opcode == 'EQ': result = (val1 == val2)
        elif opcode == 'NE': result = (val1 != val2)
        elif opcode == 'LT': result = (val1 < val2)
        elif opcode == 'LE': result = (val1 <= val2)
        elif opcode == 'GT': result = (val1 > val2)
        elif opcode == 'GE': result = (val1 >= val2)
        elif opcode == 'OR': result = (val1 or val2)
        elif opcode == 'AND': result = (val1 and val2)
        
        self._set_variable_value(target, result)
        self.pc += 1

    def _handle_string(self, instr):
        opcode, operands = instr.opcode, instr.operands
        if opcode == 'CONCAT':
            target, str1_op, str2_op = operands
            val1 = self._get_operand_value(str1_op)
            val2 = self._get_operand_value(str2_op)
            result = str(val1) + str(val2)
            self._set_variable_value(target, result)
        elif opcode == 'STRLEN':
            target, str_op = operands
            val = self._get_operand_value(str_op)
            if not isinstance(val, str):
                raise TypeError(f"STRLEN expects a string, but got {type(val).__name__} from '{str_op}'")
            self._set_variable_value(target, len(val))
        elif opcode == 'GETCHAR':
            target, str_op, index_op = operands
            string_val = self._get_operand_value(str_op)
            index_val = self._get_operand_value(index_op)
            if not isinstance(string_val, str):
                raise TypeError(f"GETCHAR expects a string, but got {type(string_val).__name__} from '{str_op}'")
            if not isinstance(index_val, int):
                raise TypeError(f"GETCHAR expects an integer index, but got {type(index_val).__name__} from '{index_op}'")
            self._set_variable_value(target, string_val[index_val])
        self.pc += 1

    def _handle_jump(self, instr):
        opcode, operands = instr.opcode, instr.operands
        if opcode == 'JUMP':
            self.pc = operands[0]
        elif opcode == 'JUMPT':
            label_target_pc, condition_var = operands
            if self._get_operand_value(condition_var):
                self.pc = label_target_pc
            else:
                self.pc += 1
        elif opcode == 'JUMPF':
            label_target_pc, condition_var = operands
            if not self._get_operand_value(condition_var):
                self.pc = label_target_pc
            else:
                self.pc += 1

    def _handle_function(self, instr):
        opcode, operands = instr.opcode, instr.operands
        if opcode == 'PARAM':
            value_to_pass = self._get_operand_value(operands[0])
            self.current_params.append(value_to_pass)
            self.pc += 1
        elif opcode == 'REF_PARAM':
            var_name = operands[0]
            addr = self._get_variable_address(var_name)
            self.current_params.append(addr) # Pass the pointer tuple directly
            self.pc += 1
        elif opcode == 'CALL':
            func_name_label, num_params_expected, return_var_name = operands
            num_params_expected = int(num_params_expected)

            if len(self.current_params) != num_params_expected:
                raise ValueError(
                    f"Function '{func_name_label}' expected {num_params_expected} parameters, but received {len(self.current_params)}")

            new_frame = StackFrame(func_name_label, self.pc + 1, return_var_name)
            
            # Parameters are copied into the new frame's 'locals' dictionary.
            # Pass-by-value copies the value.
            # Pass-by-reference copies the pointer tuple.
            for i, param_val in enumerate(self.current_params):
                arg_name = f'ARG{i}'
                new_frame.params[arg_name] = param_val # Keep original params for inspection
                new_frame.locals[arg_name] = param_val # Work with locals

            self.call_stack.append(new_frame)
            self.current_params = []
            self.pc = self.labels[func_name_label]
        elif opcode == 'RETURN':
            return_value = self._get_operand_value(operands[0]) if operands else None
            if not self.call_stack:
                raise RuntimeError("RETURN instruction outside of a function call. Halting.")

            old_frame = self.call_stack.pop()
            self.pc = old_frame.return_address

            if old_frame.return_var_name:
                self._set_variable_value(old_frame.return_var_name, return_value)

    def _handle_heap(self, instr):
        opcode, operands = instr.opcode, instr.operands
        if opcode == 'ALLOC_HEAP':
            target_ptr_var, size_var_or_literal = operands
            size_val = self._get_operand_value(size_var_or_literal)
            if not isinstance(size_val, int) or size_val <= 0:
                raise ValueError(f"ALLOC_HEAP size must be a positive integer, got '{size_val}'")

            allocated_addresses = [self._allocate_heap_slot() for _ in range(size_val)]
            for addr in allocated_addresses: self.heap[addr] = None

            if not allocated_addresses: raise MemoryError(f"Failed to allocate heap memory for size {size_val}")
            self._set_variable_value(target_ptr_var, allocated_addresses[0])
        
        elif opcode == 'FREE_HEAP':
            ptr_var = operands[0]
            ptr_addr = self._get_operand_value(ptr_var)
            if not isinstance(ptr_addr, int) or not (0 <= ptr_addr < len(self.heap)):
                self._log_console(f"Warning: FREE_HEAP called with invalid address: {ptr_addr}\n")
            else:
                self._free_heap_slot(ptr_addr)
                self._log_console(f"Note: Simplified FREE_HEAP for address {ptr_addr} called.\n")

        elif opcode == 'ADDR_OF':
            target_ptr_var, source_var = operands
            # Get the pointer/address of the source variable and store it in the target.
            pointer = self._get_variable_address(source_var)
            self._set_variable_value(target_ptr_var, pointer)

        elif opcode == 'DEREF_LOAD':
            target_var, ptr_var = operands
            pointer = self._get_operand_value(ptr_var)
            value = self._get_value_from_pointer(pointer)
            self._set_variable_value(target_var, value)

        elif opcode == 'DEREF_STORE':
            ptr_var, value_source = operands
            pointer = self._get_operand_value(ptr_var)
            value_to_store = self._get_operand_value(value_source)
            self._set_value_at_pointer(pointer, value_to_store)

        elif opcode == 'INDEX_LOAD':
            target_var, base_ptr_var, index_var = operands
            base_addr = self._get_operand_value(base_ptr_var)
            index_val = self._get_operand_value(index_var)
            if not isinstance(base_addr, int) or not (0 <= base_addr < len(self.heap)):
                raise ValueError(f"INDEX_LOAD error: Invalid base address '{base_addr}' in '{base_ptr_var}'")
            if not isinstance(index_val, int):
                raise ValueError(f"INDEX_LOAD error: Index must be an integer, got '{index_val}'")
            effective_addr = base_addr + index_val
            if not (0 <= effective_addr < len(self.heap)):
                raise IndexError(f"INDEX_LOAD error: Address {effective_addr} is out of bounds.")
            self._set_variable_value(target_var, self.heap[effective_addr])

        elif opcode == 'INDEX_STORE':
            base_ptr_var, index_var, value_source = operands
            base_addr = self._get_operand_value(base_ptr_var)
            index_val = self._get_operand_value(index_var)
            value_to_store = self._get_operand_value(value_source)
            if not isinstance(base_addr, int) or not (0 <= base_addr < len(self.heap)):
                raise ValueError(f"INDEX_STORE error: Invalid base address '{base_addr}' in '{base_ptr_var}'")
            if not isinstance(index_val, int):
                raise ValueError(f"INDEX_STORE error: Index must be an integer, got '{index_val}'")
            effective_addr = base_addr + index_val
            if not (0 <= effective_addr < len(self.heap)):
                raise IndexError(f"INDEX_STORE error: Address {effective_addr} is out of bounds.")
            self.heap[effective_addr] = value_to_store
        
        self.pc += 1

    def _handle_misc(self, instr):
        opcode, operands = instr.opcode, instr.operands
        if opcode == 'PRINT':
            value = self._get_operand_value(operands[0])
            self._log_console(f"Output: {value}\n")
            self.pc += 1
        elif opcode == 'HALT':
            self.halted = True
            self.running = False
            self.pc += 1
            self._log_console("--- Program Halted ---\n")
        elif opcode == 'UMINUS':
            target, source = operands
            val = self._get_operand_value(source)
            self._set_variable_value(target, -val)
            self.pc += 1

    def step(self):
        """Executes one 3AC instruction."""
        if not self.running or self.halted or self.pc >= len(self.program):
            self.running = False
            return False  # Program finished or halted

        instr = self.program[self.pc]
        opcode = instr.opcode

        try:
            handler = self.opcode_handlers.get(opcode)
            if handler:
                handler(instr)
            else:
                raise NotImplementedError(f"Unknown or unsupported opcode: {opcode}")

            # The HALT handler sets running to False, so this check works for halting.
            if not self.running:
                return False

            return True  # Indicate successful step

        except Exception as e:
            self.running = False
            error_msg = f"Runtime Error at 3AC line {instr.line_num} (PC={self.pc}): {e}\n"
            self._log_console(f"!!! {error_msg}")
            messagebox.showerror("Runtime Error", error_msg)
            return False  # Indicate program halted due to error