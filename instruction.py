class Instruction:
    """Represents a single 3-Address Code instruction."""

    def __init__(self, opcode, *operands, line_num=None):
        self.opcode = opcode
        self.operands = list(operands)
        self.line_num = line_num

    def __repr__(self):
        return f"Instruction({self.opcode}, {self.operands}, line={self.line_num})"