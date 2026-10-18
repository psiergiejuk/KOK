# core/model.py

class ProgramModel:
    def __init__(self):
        # Słownik lub lista przechowująca kod: { numer_linii: "tekst_komendy" }
        self.lines = {}
        # Pamięć zmiennych stworzonych przez użytkownika (np. {"A": 10})
        self.variables = {}
        # Wskaźnik aktualnie wykonywanej linii (do pętli / skoków)
        self.current_line_index = 0

    def clear(self):
        self.lines.clear()
        self.variables.clear()
        self.current_line_index = 0

    def set_line(self, number: int, code: str):
        if code.strip() == "":
            self.lines.pop(number, None)
        else:
            self.lines[number] = code

    def get_sorted_code(self):
        # Zwraca posortowane linijki kodu gotowe do wykonania
        return [self.lines[k] for k in sorted(self.lines.keys())]
