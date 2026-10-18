# editor/console.py
import pygame

AVAILABLE_COMMANDS = {
    "print": "PRINT tekst -> Wypisuje tekst na ekranie",
    "circle": "CIRCLE x, y, r -> Rysuje okrąg w punkcie x, y o promieniu r",
    "rect": "RECT x, y, w, h -> Rysuje prostokąt o szerokości w i wysokości h",
    "color": "COLOR nazwa -> Zmienia kolor rysowania (np. yellow, red)",
    "cls": "CLS -> Czyści ekran",
    "run": "RUN -> Uruchamia wpisany program"
}

class Console:
    def __init__(self, model):
        self.model = model
        self.current_input = ""
        self.font = pygame.font.SysFont("Courier", 24)
        self.doc_font = pygame.font.SysFont("Courier", 18)
        
        self.suggestions = []
        self.focus_on_suggestions = False
        self.selected_index = 0

    def handle_event(self, event):
        """Obsługuje zdarzenia klawiatury dla konsoli i podpowiadacza"""
        if event.type != pygame.KEYDOWN:
            return

        # 1. Gdy focus jest na podpowiadaczu
        if self.focus_on_suggestions:
            if event.key == pygame.K_TAB:
                if self.suggestions:
                    self.selected_index = (self.selected_index + 1) % len(self.suggestions)
            elif event.key == pygame.K_RETURN:
                if self.suggestions:
                    chosen = self.suggestions[self.selected_index]
                    self.current_input = chosen.upper() + " "
                self.close_suggestions()
            else:
                self.close_suggestions()
                self.handle_editor_input(event)
        
        # 2. Gdy focus jest w edytorze tekstu
        else:
            if event.key == pygame.K_RETURN:
                self.process_input()
                self.close_suggestions()
            elif event.key == pygame.K_BACKSPACE:
                self.current_input = self.current_input[:-1]
                self.update_suggestions()
            elif event.key == pygame.K_TAB:
                if not self.suggestions:
                    self.update_suggestions(force_all=True)
                
                if self.suggestions:
                    self.focus_on_suggestions = True
                    self.selected_index = 0
            else:
                if event.unicode.isprintable():
                    self.current_input += event.unicode
                    self.update_suggestions()

    def update_suggestions(self, force_all=False):
        """Aktualizuje listę podpowiedzi na podstawie wpisanego tekstu"""
        text = self.current_input.strip().lower()
        if force_all or not text:
            self.suggestions = list(AVAILABLE_COMMANDS.keys())
        elif " " in text:
            self.suggestions = []
        else:
            self.suggestions = [cmd for cmd in AVAILABLE_COMMANDS.keys() if cmd.startswith(text)]
        
        self.selected_index = 0

    def close_suggestions(self):
        """Resetuje stan podpowiadacza i oddaje focus edytorowi"""
        self.focus_on_suggestions = False
        self.suggestions = []
        self.selected_index = 0

    def handle_editor_input(self, event):
        """Obsługuje wpisywanie znaków po powrocie focusu do edytora"""
        if event.key == pygame.K_BACKSPACE:
            self.current_input = self.current_input[:-1]
        elif event.unicode.isprintable():
            self.current_input += event.unicode
        self.update_suggestions()

    def process_input(self):
        """Przetwarza zatwierdzoną linię kodu"""
        line_text = self.current_input.strip()
        if not line_text:
            return

        parts = line_text.split(" ", 1)
        if parts[0].isdigit():
            line_num = int(parts[0])
            code = parts[1] if len(parts) > 1 else ""
            self.model.set_line(line_num, code)
        else:
            print(f"Komenda natychmiastowa: {line_text}")

        self.current_input = ""

    def draw(self, surface):
        """Rysuje linię zachęty oraz podpowiadacz z uwzględnieniem focusu i pojedynczego wyniku"""
        screen_height = surface.get_height()
        base_y = screen_height - 60

        # 1. Główna linia wprowadzania
        prompt_text = f"> {self.current_input}_"
        prompt_surf = self.font.render(prompt_text, True, (255, 236, 39))
        surface.blit(prompt_surf, (40, base_y))

        # 2. Rysowanie podpowiadacza
        if self.suggestions:
            if len(self.suggestions) == 1:
                # Jeśli została dokładnie jedna opcja -> wyświetlamy od razu jej dokumentację (doc)
                cmd_name = self.suggestions[0]
                doc_text = f"doc: {AVAILABLE_COMMANDS[cmd_name]}"
                doc_surf = self.doc_font.render(doc_text, True, (41, 173, 255))
                surface.blit(doc_surf, (40, base_y + 35))
            else:
                # Jeśli jest wiele opcji do wyboru (np. po wciśnięciu TAB na pustym)
                x_offset = 40
                for i, cmd in enumerate(self.suggestions):
                    is_active = self.focus_on_suggestions and (i == self.selected_index)
                    
                    if is_active:
                        color = (0, 228, 54)  # Zielony dla zaznaczonej
                        prefix = "[ "
                        suffix = " ]"
                    else:
                        color = (150, 150, 150) # Szary dla pozostałych
                        prefix = "  "
                        suffix = "  "

                    item_surf = self.doc_font.render(f"{prefix}{cmd.upper()}{suffix}", True, color)
                    surface.blit(item_surf, (x_offset, base_y + 35))
                    x_offset += item_surf.get_width() + 10

                # Jeśli podpowiadacz ma focus, pokazujemy dodatkowo opis wybranej pozycji
                if self.focus_on_suggestions:
                    active_cmd = self.suggestions[self.selected_index]
                    doc_text = f"doc: {AVAILABLE_COMMANDS[active_cmd]}"
                    doc_surf = self.doc_font.render(doc_text, True, (41, 173, 255))
                    surface.blit(doc_surf, (40, base_y + 60))
