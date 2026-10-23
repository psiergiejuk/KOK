import re
from core.commands.print_cmd import PrintCommand
from core.commands.cls_cmd import ClsCommand
from core.commands.let_cmd import LetCommand

class CommandRegistry:
    def __init__(self):
        self.commands = {}
        self.variables = {}
        self.register(PrintCommand(self))
        self.register(ClsCommand(self))
        self.register(LetCommand(self))
        
    def register(self, command_instance):
        self.commands[command_instance.name.upper()] = command_instance
        
    def execute_command(self, line: str, console_lines: list, variables: dict = None) -> tuple[bool, bool]:
        if variables is None:
            variables = self.variables

        trimmed = line.strip()
        if not trimmed:
            return False, False

        # Sprawdzamy czy to przypisanie bez słowa LET (np. A = 5 lub IMIE$ = "Kuba")
        if "=" in trimmed and not trimmed.upper().startswith("IF "):
            left, _, right = trimmed.partition("=")
            var_candidate = left.strip().upper()
            if re.match(r'^[A-Z_][A-Z0-9_]*\$?$', var_candidate):
                success = self.commands["LET"].execute_assignment(var_candidate, right.strip(), console_lines, variables)
                return True, success

        parts = trimmed.split()
        cmd_name = parts[0].upper()
        if cmd_name in self.commands:
            success = self.commands[cmd_name].execute(line, console_lines, variables)
            return True, success
            
        return False, False
