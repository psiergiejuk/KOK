import re
from core.commands.help_cmd import HelpCommand
from core.commands.print_cmd import PrintCommand
from core.commands.cls_cmd import ClsCommand
from core.commands.let_cmd import LetCommand
from core.commands.history_cmd import HistoryCommand
from core.commands.quiz_cmd import QuizCommand
from core.commands.for_cmd import ForCommand
from core.commands.date_cmd import DateCommand
from core.commands.time_cmd import TimeCommand
from core.commands.pause_cmd import PauseCommand
from core.commands.vars_cmd import VarsCommand, ClearCommand
from core.commands.if_cmd import IfCommand
from core.commands.gfx_cmd import ColorCommand, PixelCommand, LineCommand, CircleCommand, RectCommand, TextCommand
from core.commands.gpio_cmd import OutCommand, InCommand
from core.commands.sound_cmd import BeepCommand, SoundCommand, PlayCommand
from core.commands.basic_cmd import (
    RemCommand,
    InputCommand,
    DimCommand,
    RandomizeCommand,
    EndCommand,
    GotoCommand,
    WhileCommand,
    WendCommand,
)
from core.commands.program_cmd import (
    NewCommand,
    EditCommand,
    ListCommand,
    SaveCommand,
    LoadCommand,
    FilesCommand,
    RunCommand,
    CheckCommand,
    HintCommand,
)

class CommandRegistry:
    def __init__(self):
        self.commands = {}
        self.variables = {}
        self.history = []
        self.graphics_items = []
        self.current_color = (80, 255, 120)
        self.gpio_pins = [False] * 8
        self.program_lines = [""]
        self.current_program_name = "PROGRAM"
        self.saved_programs = {}
        self.open_editor_requested = False
        self.on_pause = None
        self.on_input = None
        self.input_queue = []
        self.active_user_data = None
        self.active_task = None
        self.last_check_result = None
        self.last_hint_result = None
        self.register(HelpCommand(self))
        self.register(PrintCommand(self))
        self.register(ClsCommand(self))
        self.register(LetCommand(self))
        self.register(HistoryCommand(self))
        self.register(QuizCommand(self))
        self.register(ForCommand(self))
        self.register(DateCommand(self))
        self.register(TimeCommand(self))
        self.register(PauseCommand(self))
        self.register(VarsCommand(self))
        self.register(ClearCommand(self))
        self.register(IfCommand(self))
        self.register(ColorCommand(self))
        self.register(PixelCommand(self))
        self.register(LineCommand(self))
        self.register(CircleCommand(self))
        self.register(RectCommand(self))
        self.register(TextCommand(self))
        self.register(OutCommand(self))
        self.register(InCommand(self))
        self.register(BeepCommand(self))
        self.register(SoundCommand(self))
        self.register(PlayCommand(self))
        self.register(RemCommand(self))
        self.register(InputCommand(self))
        self.register(DimCommand(self))
        self.register(RandomizeCommand(self))
        self.register(EndCommand(self))
        self.register(GotoCommand(self))
        self.register(WhileCommand(self))
        self.register(WendCommand(self))
        self.register(NewCommand(self))
        self.register(EditCommand(self))
        self.register(ListCommand(self))
        self.register(SaveCommand(self))
        self.register(LoadCommand(self))
        self.register(FilesCommand(self))
        self.register(RunCommand(self))
        self.register(CheckCommand(self))
        self.register(HintCommand(self))

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

        # Sprawdzamy czy to przypisanie bez słowa LET (np. A = 5, IMIE$ = "Kuba", albo A(1) = 50)
        if "=" in trimmed and not trimmed.upper().startswith(("IF ", "PRINT ", "FOR ", "WHILE ")):
            left, _, right = trimmed.partition("=")
            var_candidate = left.strip().upper()
            if re.match(r'^[A-Z_][A-Z0-9_]*\$?(\(.+\))?$', var_candidate):
                success = self.commands["LET"].execute_assignment(var_candidate, right.strip(), console_lines, variables)
                return True, success

        parts = trimmed.split()
        cmd_name = parts[0].upper()
        if cmd_name in self.commands:
            success = self.commands[cmd_name].execute(line, console_lines, variables)
            return True, success

        return False, False
