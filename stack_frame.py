class StackFrame:
    """Represents an activation record for a function call."""

    def __init__(self, func_name, return_address, return_var_name=None):
        self.func_name = func_name
        self.return_address = return_address  # PC to return to
        self.return_var_name = return_var_name  # Variable to store return value in caller's frame
        self.locals = {}  # Local variables
        self.params = {}  # Parameters (can be values or addresses for pass-by-reference)

    def __repr__(self):
        return (f"Frame(func='{self.func_name}', ret_addr={self.return_address}, "
                f"locals={self.locals}, params={self.params})")