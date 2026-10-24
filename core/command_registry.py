import re
from core.commands.help_cmd import HelpCommand
from core.commands.print_cmd import PrintCommand
from core.commands.cls_cmd import ClsCommand
from core.commands.let_cmd import LetCommand
from core.commands.history_cmd import HistoryCommand
from core.commands.quiz_cmd import QuizCommand
from core.commands.for_cmd import ForCommand

class CommandRegistry:
    def __init__(self):
        self.commands = {}
        self.variables = {}
        self.history = []
        self.register(HelpCommand(self))
        self.register(PrintCommand(self))
        self.register(ClsCommand(self))
        self.register(LetCommand(self))
        self.register(HistoryCommand(self))
        self.register(QuizCommand(self))
        self.register(ForCommand(self))
        
    def register(self, command_instance):
        help_lines = command_instance.get_help()
        if not help_lines or not isinstance(help_lines, list):
            raise ValueError(f"Komenda {command_instance.name} musi posiadać niepusty opis get_help()!")
        self.commands[command_instance.name.upper()] = command_instance
        for alias in getattr(command_instance, "aliases", []):
            self.commands[alias.upper()] = command_instance

    def get_command_help(self, name: str) -> list[str] | None:
        cmd = self.commands.get(name.upper())
        if cmd:
            return cmd.get_help()
        if name.upper() in HelpCommand.EXTRA_HELP:
            return HelpCommand.EXTRA_HELP[name.upper()]
        return None
        
    def execute_command(self, line: str, console_lines: list, variables: dict = None, record_history: bool = True) -> tuple[bool, bool]:
        if variables is None:
            variables = self.variables

        trimmed = line.strip()
        if not trimmed:
            return False, False

        if record_history:
            self.history.append(trimmed)

        # Sprawdzamy czy to przypisanie bez słowa LET (np. A = 5 lub IMIE$ = "Kuba")
        if "=" in trimmed and not trimmed.upper().startswith(("IF ", "PRINT ", "FOR ")):
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
