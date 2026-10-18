# core/interpreter.py
import importlib

class Interpreter:
    def __init__(self, model, display):
        self.model = model
        self.display = display

    def run_program(self):
        code_lines = self.model.get_sorted_code()
        
        for line in code_lines:
            parts = line.strip().split(" ", 1)
            cmd_name = parts[0].lower()
            
            # Pobranie argumentów (jeśli istnieją)
            args = []
            if len(parts) > 1:
                # Dzielimy argumenty po przecinku i usuwamy spacje
                args = [arg.strip() for arg in parts[1].split(",")]

            # Dynamiczne ładowanie komendy z folderu commands/
            try:
                module = importlib.import_module(f"commands.{cmd_name}")
                module.execute(self.model, self.display, args)
            except ModuleNotFoundError:
                print(f"Nieznana komenda: {cmd_name}")
