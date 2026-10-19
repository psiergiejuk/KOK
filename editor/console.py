import json
import pygame
from core.user_manager import UserManager
from core.command_registry import CommandRegistry
from core.quest_validator import QuestValidator

def print_next_available_task(tasks, user_data, console_lines):
    completed = set(user_data.get("completed_tasks", []))
    for task in tasks:
        if task["id"] not in completed:
            console_lines.append("")
            console_lines.append(f"ZADANIE: {task['title']}")
            if "instruction" in task:
                console_lines.append(f"CO ZROBIĆ: {task['instruction']}")
            console_lines.append("")
            return
    console_lines.append("")
    console_lines.append("🎉 BRAWO! Wszystkie dostępne zadania w tym poziomie zostały ukończone!")
    console_lines.append("")

class RetroConsoleManager:
    def __init__(self, font):
        self.font = font
        self.manager = UserManager()
        self.command_registry = CommandRegistry()
        
        # Stany aplikacji
        self.STATE_USERNAME = "USERNAME"
        self.STATE_PASSWORD = "PASSWORD"
        self.STATE_REG_FIRST = "REG_FIRST"
        self.STATE_REG_LAST = "REG_LAST"
        self.STATE_REG_AGE = "REG_AGE"
        self.STATE_REG_PASS = "REG_PASS"
        self.STATE_CONSOLE = "CONSOLE"
        self.STATE_CONFIRM_RESET = "CONFIRM_RESET"
        
        self.current_state = self.STATE_USERNAME
        self.input_text = ""
        self.cursor_pos = 0
        self.temp_user = {}
        self.user_data = None
        
        self.console_lines = [
            "WITAJ W MINIMALISTYCZNYM EMULATORZE KOK BASIC",
            "--------------------------------------------",
            "Podaj nazwę użytkownika (login):"
        ]
        
        self.tasks = []
        try:
            with open("config/tech_tree.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
                self.tasks = cfg.get("tasks", [])
        except Exception:
            pass

    def handle_keydown(self, event) -> bool:
        if event.key == pygame.K_ESCAPE:
            if self.user_data:
                self.manager.save_user_state(self.user_data)
            return False
            
        elif event.key == pygame.K_LEFT:
            self.cursor_pos = max(0, self.cursor_pos - 1)
            
        elif event.key == pygame.K_RIGHT:
            self.cursor_pos = min(len(self.input_text), self.cursor_pos + 1)
            
        elif event.key == pygame.K_BACKSPACE:
            if self.cursor_pos > 0:
                self.input_text = self.input_text[:self.cursor_pos - 1] + self.input_text[self.cursor_pos:]
                self.cursor_pos -= 1
                
        elif event.key == pygame.K_DELETE:
            if self.cursor_pos < len(self.input_text):
                self.input_text = self.input_text[:self.cursor_pos] + self.input_text[self.cursor_pos + 1:]
                
        elif event.key == pygame.K_RETURN:
            line = self.input_text.strip()
            self.input_text = ""
            self.cursor_pos = 0
            
            if self.current_state == self.STATE_USERNAME:
                if not line:
                    return True
                self.temp_user["username"] = line
                self.console_lines.append(f"> {line}")
                
                if self.manager.user_exists(line):
                    self.console_lines.append(f"Użytkownik '{line}' istnieje.")
                    self.console_lines.append("Podaj hasło:")
                    self.current_state = self.STATE_PASSWORD
                else:
                    self.console_lines.append(f"Nie znaleziono '{line}'. Tworzymy nowy profil.")
                    self.console_lines.append("Podaj swoje imię:")
                    self.current_state = self.STATE_REG_FIRST
                    
            elif self.current_state == self.STATE_PASSWORD:
                username = self.temp_user["username"]
                self.user_data = self.manager.authenticate_user(username, line)
                self.console_lines.append("> ****")
                if self.user_data:
                    self.console_lines.append(f"Zalogowano pomyślnie! Witaj, {self.user_data['first_name']}.")
                    unlocked = self.user_data.get('unlocked_techs', [])
                    self.console_lines.append(f"Odblokowane technologie: {', '.join(unlocked) if unlocked else 'Brak'}")
                    max_sp = sum(t.get("reward_sp", 1) for t in self.tasks)
                    self.console_lines.append(f"Punkty SP: {self.user_data['science_points']} / {max_sp}")
                    print_next_available_task(self.tasks, self.user_data, self.console_lines)
                    self.current_state = self.STATE_CONSOLE
                else:
                    self.console_lines.append("Błędne hasło! Podaj hasło ponownie:")
                    
            elif self.current_state == self.STATE_REG_FIRST:
                self.temp_user["first_name"] = line
                self.console_lines.append(f"> {line}")
                self.console_lines.append("Podaj swoje nazwisko:")
                self.current_state = self.STATE_REG_LAST
                
            elif self.current_state == self.STATE_REG_LAST:
                self.temp_user["last_name"] = line
                self.console_lines.append(f"> {line}")
                self.console_lines.append("Podaj swój wiek:")
                self.current_state = self.STATE_REG_AGE
                
            elif self.current_state == self.STATE_REG_AGE:
                if line.isdigit():
                    self.temp_user["age"] = int(line)
                    self.console_lines.append(f"> {line}")
                    self.console_lines.append("Utwórz hasło do konta:")
                    self.current_state = self.STATE_REG_PASS
                else:
                    self.console_lines.append("Wiek musi być liczbą! Podaj wiek:")
                    
            elif self.current_state == self.STATE_REG_PASS:
                self.console_lines.append("> ****")
                self.user_data = self.manager.register_user(
                    username=self.temp_user["username"],
                    first_name=self.temp_user["first_name"],
                    last_name=self.temp_user["last_name"],
                    age=self.temp_user["age"],
                    password=line
                )
                self.console_lines.append("Konto utworzone i zalogowane pomyślnie!")
                self.console_lines.append(f"Witaj, {self.user_data['first_name']}!")
                print_next_available_task(self.tasks, self.user_data, self.console_lines)
                self.current_state = self.STATE_CONSOLE
                
            elif self.current_state == self.STATE_CONFIRM_RESET:
                self.console_lines.append(f"> {line}")
                if line.upper() in ["T", "TAK", "Y", "YES"]:
                    if self.user_data and "username" in self.user_data:
                        self.manager.delete_user(self.user_data["username"])
                    self.console_lines.append("🗑️ Dane zostały zresetowane, a profil usunięty.")
                    self.console_lines.append("--------------------------------------------")
                    self.console_lines.append("Podaj nazwę użytkownika (login):")
                    self.user_data = None
                    self.temp_user = {}
                    self.current_state = self.STATE_USERNAME
                else:
                    self.console_lines.append("Anulowano resetowanie danych.")
                    self.current_state = self.STATE_CONSOLE
                
            elif self.current_state == self.STATE_CONSOLE:
                if not line:
                    return True
                self.console_lines.append(f"KOK-BASIC> {line}")
                
                if line.upper() == "EXIT":
                    self.manager.save_user_state(self.user_data)
                    return False
                    
                if line.upper() == "_RESET":
                    self.console_lines.append("⚠️ UWAGA: Czy na pewno chcesz usunąć profil i zresetować wszystkie postępy? (T/N)")
                    self.current_state = self.STATE_CONFIRM_RESET
                    return True
                    
                found, success = self.command_registry.execute_command(line, self.console_lines)
                
                if not found:
                    self.console_lines.append(f"SYNTAX ERROR: Nieznana komenda '{line.split()[0]}'")
                    return True

                if success:
                    cmd_name = line.split()[0].upper()
                    if "action_counts" not in self.user_data:
                        self.user_data["action_counts"] = {}
                    self.user_data["action_counts"][cmd_name] = self.user_data["action_counts"].get(cmd_name, 0) + 1
                    
                    task_completed_now = False
                    for task in self.tasks:
                        task_id = task["id"]
                        if task_id in self.user_data["completed_tasks"]:
                            continue
                            
                        if QuestValidator.validate(task, line, self.user_data):
                            reward = task.get("reward_sp", 1)
                            self.user_data["science_points"] += reward
                            self.user_data["completed_tasks"].append(task_id)
                            
                            max_sp = sum(t.get("reward_sp", 1) for t in self.tasks)
                            self.console_lines.append(f"✅ ZADANIE ZALICZONE! (+{reward} SP)")
                            self.console_lines.append(f"Punkty SP: {self.user_data['science_points']} / {max_sp}")
                            self.manager.save_user_state(self.user_data)
                            task_completed_now = True
                            break
                    
                    if task_completed_now:
                        print_next_available_task(self.tasks, self.user_data, self.console_lines)
        else:
            if event.unicode and event.unicode.isprintable():
                self.input_text = self.input_text[:self.cursor_pos] + event.unicode + self.input_text[self.cursor_pos:]
                self.cursor_pos += 1

        return True

    def draw(self, screen, width, height):
        line_height = 30
        max_lines = (height - 120) // line_height
        
        visible_lines = self.console_lines[-max_lines:]
        num_lines = len(visible_lines)
        
        bottom_limit = height - 90
        start_y = bottom_limit - (num_lines * line_height)
        y_offset = max(40, start_y)
        
        for line in visible_lines:
            if line.startswith("ZADANIE:") or line.startswith("CO ZROBIĆ:"):
                color = (255, 215, 0)
            elif line.startswith("⚠️") or line.startswith("🗑️") or "SYNTAX ERROR" in line:
                color = (255, 100, 100)
            elif "✅" in line or "Zalogowano" in line or "BRAWO" in line:
                color = (100, 255, 100)
            else:
                color = (200, 200, 220)
                
            text_surface = self.font.render(line, True, color)
            screen.blit(text_surface, (50, y_offset))
            y_offset += line_height

        prompt_symbol = "KOK-BASIC> " if self.current_state == self.STATE_CONSOLE else ">> "
        if self.current_state == self.STATE_CONFIRM_RESET:
            prompt_symbol = "RESET (T/N)> "
            
        if self.current_state in [self.STATE_PASSWORD, self.STATE_REG_PASS]:
            display_text = "*" * len(self.input_text)
        else:
            display_text = self.input_text

        text_left = display_text[:self.cursor_pos]
        text_right = display_text[self.cursor_pos:]

        x_cursor_pos = 50
        
        prompt_surf = self.font.render(prompt_symbol, True, (255, 255, 0))
        screen.blit(prompt_surf, (x_cursor_pos, height - 60))
        x_cursor_pos += prompt_surf.get_width()

        if text_left:
            left_surf = self.font.render(text_left, True, (255, 255, 0))
            screen.blit(left_surf, (x_cursor_pos, height - 60))
            x_cursor_pos += left_surf.get_width()

        cursor_surf = self.font.render("_", True, (255, 255, 0))
        screen.blit(cursor_surf, (x_cursor_pos, height - 60))
        x_cursor_pos += cursor_surf.get_width()

        if text_right:
            right_surf = self.font.render(text_right, True, (255, 255, 0))
            screen.blit(right_surf, (x_cursor_pos, height - 60))
