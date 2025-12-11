import unittest
from unittest.mock import patch

from instruction import Instruction
from stack_frame import StackFrame
from vm import VM


class DummyConsoleOutput:
    """A mock object to simulate the Tkinter text widget for console output."""
    def __init__(self):
        self.messages = []

    def insert(self, index, message):
        self.messages.append(message)

    def delete(self, start, end):
        self.messages = []

    def see(self, index):
        pass  # No-op for testing

    def get_messages(self):
        return "".join(self.messages)


class TestVM(unittest.TestCase):
    """Unit tests for the Virtual Machine (VM) class."""

    def setUp(self):
        """Set up a fresh VM instance for each test."""
        self.console_mock = DummyConsoleOutput()
        # We patch messagebox to prevent GUI popups during tests
        self.messagebox_patcher = patch('vm.messagebox')
        self.mock_messagebox = self.messagebox_patcher.start()
        
        self.vm = VM(console_output_widget=self.console_mock)
        self.vm.reset_state()

    def tearDown(self):
        """Stop the patcher after each test."""
        self.messagebox_patcher.stop()

    def test_load_program_simple(self):
        """Tests loading a basic program with an assignment."""
        code = ["ASSIGN x, 10", "HALT"]
        self.vm.load_program(code)
        self.assertEqual(len(self.vm.program), 2)
        self.assertEqual(self.vm.program[0].opcode, 'ASSIGN')
        self.assertEqual(self.vm.program[0].operands, ['x', 10])
        self.assertEqual(self.vm.program[1].opcode, 'HALT')

    def test_load_program_with_labels(self):
        """Tests if labels are correctly parsed and jumps are resolved."""
        code = [
            "JUMP my_label",
            "HALT",
            "my_label:",
            "ASSIGN y, 20"
        ]
        self.vm.load_program(code)
        self.assertIn('my_label', self.vm.labels)
        self.assertEqual(self.vm.labels['my_label'], 2)  # PC for instruction after label
        
        jump_instr = self.vm.program[0]
        self.assertEqual(jump_instr.opcode, 'JUMP')
        # Check that the label name was replaced with the PC index
        self.assertEqual(jump_instr.operands[0], 2)

    def test_load_program_undefined_label(self):
        """Tests that loading a program with an undefined label raises an error."""
        code = ["JUMP non_existent_label"]
        with self.assertRaisesRegex(ValueError, "Undefined label 'non_existent_label'"):
            self.vm.load_program(code)

    def test_step_assignment(self):
        """Tests the ASSIGN instruction."""
        code = ["ASSIGN x, 100"]
        self.vm.load_program(code)
        self.vm.step()
        self.assertEqual(self.vm.global_memory.get('x'), 100)
        self.assertEqual(self.vm.pc, 1)

    def test_step_arithmetic(self):
        """Tests an arithmetic instruction like ADD."""
        code = [
            "ASSIGN a, 5",
            "ADD res, a, 3"
        ]
        self.vm.load_program(code)
        self.vm.step()  # Execute ASSIGN
        self.vm.step()  # Execute ADD
        self.assertEqual(self.vm.global_memory.get('res'), 8)
        self.assertEqual(self.vm.pc, 2)

    def test_step_division_by_zero(self):
        """Tests that division by zero halts execution and shows an error."""
        code = ["DIV res, 10, 0"]
        self.vm.load_program(code)
        
        result = self.vm.step()
        
        self.assertFalse(result)  # Step should fail
        self.assertFalse(self.vm.running)
        self.assertIn("Division by zero", self.console_mock.get_messages())
        self.mock_messagebox.showerror.assert_called_once()

    def test_step_jump(self):
        """Tests an unconditional JUMP instruction."""
        code = [
            "JUMP target",
            "ASSIGN x, 1", # This should be skipped
            "target:",
            "ASSIGN y, 2"
        ]
        self.vm.load_program(code)
        self.vm.step() # Execute JUMP
        self.assertEqual(self.vm.pc, 2)
        self.vm.step() # Execute ASSIGN y, 2
        self.assertEqual(self.vm.global_memory.get('y'), 2)
        self.assertIsNone(self.vm.global_memory.get('x'))

    def test_step_conditional_jump_true(self):
        """Tests JUMPT when the condition is true."""
        code = [
            "ASSIGN cond, true",
            "JUMPT target, cond",
            "ASSIGN x, 1", # Skipped
            "target:",
            "ASSIGN y, 2"
        ]
        self.vm.load_program(code)
        self.vm.step() # ASSIGN
        self.vm.step() # JUMPT
        self.assertEqual(self.vm.pc, 3)

    def test_step_conditional_jump_false(self):
        """Tests JUMPF when the condition is false."""
        code = [
            "ASSIGN cond, false",
            "JUMPF target, cond",
            "ASSIGN x, 1", # Skipped
            "target:",
            "ASSIGN y, 2"
        ]
        self.vm.load_program(code)
        self.vm.step() # ASSIGN
        self.vm.step() # JUMPF
        self.assertEqual(self.vm.pc, 3)

    def test_function_call_and_return(self):
        """Tests a full function call cycle with PARAM, CALL, and RETURN."""
        code = [
            "PARAM 10",
            "CALL my_func, 1, result",
            "HALT",
            "my_func:",
            "ADD temp, ARG0, 5",
            "RETURN temp"
        ]
        self.vm.load_program(code)

        # Step 1: PARAM 10
        self.vm.step()
        self.assertEqual(self.vm.current_params, [10])

        # Step 2: CALL my_func
        self.vm.step()
        self.assertEqual(self.vm.pc, 3) # Jumped to function
        self.assertEqual(len(self.vm.call_stack), 1)
        frame = self.vm.call_stack[0]
        self.assertEqual(frame.func_name, 'my_func')
        self.assertEqual(frame.return_address, 2)
        self.assertEqual(frame.params['ARG0'], 10)

        # Step 3: ADD temp, ARG0, 5
        self.vm.step()
        self.assertEqual(frame.locals['temp'], 15)

        # Step 4: RETURN temp
        self.vm.step()
        self.assertEqual(self.vm.pc, 2) # Returned to instruction after CALL
        self.assertEqual(len(self.vm.call_stack), 0)
        self.assertEqual(self.vm.global_memory['result'], 15)

    def test_heap_alloc_and_dereference(self):
        """Tests ALLOC_HEAP, DEREF_STORE, and DEREF_LOAD."""
        code = [
            "ALLOC_HEAP ptr, 1",
            "DEREF_STORE ptr, 123",
            "DEREF_LOAD val, ptr"
        ]
        self.vm.load_program(code)

        # Step 1: ALLOC_HEAP
        self.vm.step()
        ptr_addr = self.vm.global_memory.get('ptr')
        self.assertIsInstance(ptr_addr, int)

        # Step 2: DEREF_STORE
        self.vm.step()
        self.assertEqual(self.vm.heap[ptr_addr], 123)

        # Step 3: DEREF_LOAD
        self.vm.step()
        self.assertEqual(self.vm.global_memory.get('val'), 123)


if __name__ == '__main__':
    unittest.main()