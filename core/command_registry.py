from core.commands.print_cmd import PrintCommand
from core.commands.cls_cmd import ClsCommand

class CommandRegistry:
    def __init__(self):
        self.commands = {}
        self.register(PrintCommand())
        self.register(ClsCommand())
        
    def register(self, command_instance):
        self.commands[command_instance.name.upper()] = command_instance
        
    def execute_command(self, line: str, console_lines: list) -> tuple[bool, bool]:
        parts = line.split()
        if not parts:
            return False, False
            
        cmd_name = parts[0].upper()
        if cmd_name in self.commands:
            success = self.commands[cmd_name].execute(line, console_lines)
            return True, success
            
        return False, False
