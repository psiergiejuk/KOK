import json
import math
import array
import pygame
from core.user_manager import UserManager
from core.command_registry import CommandRegistry
from core.quest_validator import QuestValidator

def play_retro_victory_sound():
    """Generuje i odtwarza retro dźwięk w stylu Pegasusa/chiptune."""
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=22050, size=-16, channels=1)
        sample_rate = 22050
        def make_tone(freq, duration):
            num_samples = int(sample_rate * duration)
            buf = array.array('h', [int(32767 * 0.3 * math.sin(2 * math.pi * freq * i / sample_rate)) for i in range(num_samples)])
            return pygame.mixer.Sound(buffer=buf)

        # Szybkie radosne arpeggio
        for f in [523.25, 659.25, 783.99, 1046.50]:
            s = make_tone(f, 0.08)
            s.play()
            pygame.time.delay(70)
    except Exception:
        pass

def print_next_available_task(tasks, user_data, console_lines):
    """Wyświetla kolejne dostępne zadanie tylko z odblokowanych technologii."""
    completed = set(user_data.get("completed_tasks", []))
    unlocked_techs = set(user_data.get("unlocked_techs", []))

    for task in tasks:
        tech_id = task.get("tech_id")
        if tech_id in unlocked_techs and task["id"] not in completed:
            console_lines.append("")
            console_lines.append(f"ZADANIE: {task['title']}")
            if "instruction" in task:
                console_lines.append(f"CO ZROBIĆ: {task['instruction']}")
            console_lines.append("")
            return

class RetroConsoleManager:
    def __init__(self, font):
        self.font = font
        self.manager = UserManager()
        self.command_registry = CommandRegistry()

        self.STATE_USERNAME = "USERNAME"
        self.STATE_PASSWORD = "PASSWORD"
        self.STATE_REG_FIRST = "REG_FIRST"
        self.STATE_REG_LAST = "REG_LAST"
        self.STATE_REG_AGE = "REG_AGE"
        self.STATE_REG_PASS = "REG_PASS"
        self.STATE_CONSOLE = "CONSOLE"
        self.STATE_SELECT_TECH = "SELECT_TECH"
        self.STATE_CONFIRM_RESET = "CONFIRM_RESET"

        self.current_state = self.STATE_USERNAME
        self.input_text = ""
        self.cursor_pos = 0
        self.temp_user = {}
        self.user_data = None
        self.available_techs_to_pick = []

        self.console_lines = [
            "WITAJ W MINIMALISTYCZNYM EMULATORZE KOK BASIC",
            "--------------------------------------------",
            "Podaj nazwę użytkownika (login):"
        ]

        self.tasks = []
        self.technologies = []
        try:
            with open("config/tech_tree.json", "r", encoding="utf-8") as f:
                root_cfg = json.load(f)
                tech_files = root_cfg.get("technologies_files", [])

                for file_path in tech_files:
                    with open(file_path, "r", encoding="utf-8") as tf:
                        tech_data = json.load(tf)
                        tech_tasks = tech_data.pop("tasks", [])

                        # Zapisujemy identyfikatory zadań w technologii
                        tech_data["task_ids"] = [t["id"] for t in tech_tasks]

                        for t in tech_tasks:
                            t["tech_id"] = tech_data["id"]
                            self.tasks.append(t)
                        self.technologies.append(tech_data)
        except Exception as e:
            print(f"Błąd ładowania konfiguracji technologii: {e}")

    def check_tech_completion(self):
        """Sprawdza, czy gracz ukończył wszystkie zadania dla aktywnej technologii i może kupić kolejną."""
        completed = set(self.user_data.get("completed_tasks", []))
        unlocked = set(self.user_data.get("unlocked_techs", []))

        self.available_techs_to_pick = []
        for tech in self.technologies:
            tech_id = tech["id"]
            if tech_id in unlocked:
                continue

            requires = tech.get("requires", [])
            if all(req in unlocked for req in requires):
                req_tasks_completed = True
                for req_id in requires:
                    req_tech = next((t for t in self.technologies if t["id"] == req_id), None)
                    if req_tech:
                        for tid in req_tech.get("task_ids", []):
                            if tid not in completed:
                                req_tasks_completed = False
                                break

                if req_tasks_completed:
                    self.available_techs_to_pick.append(tech)

        if self.available_techs_to_pick and self.current_state == self.STATE_CONSOLE:
            play_retro_victory_sound()
            self.console_lines.append("")
            self.console_lines.append("🎉 HURA! NOWY POZIOM DOSTĘPNY! 🎉")
            self.console_lines.append("Wybierz technologię do odblokowania, wpisując jej numer i wciskając ENTER:")
            for idx, tech in enumerate(self.available_techs_to_pick, 1):
                self.console_lines.append(f"  [{idx}] {tech['name']} (Koszt: {tech['cost']} SP)")
            self.console_lines.append("")
            self.current_state = self.STATE_SELECT_TECH

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

            # --- STANY REJESTRACJI I LOGOWANIA ---
            if self.current_state == self.STATE_USERNAME:
                if not line:
                    return True
                self.temp_user["username"] = line
                self.console_lines.append(f"> {line}")
                if self.manager.user_exists(line):
                    self.console_lines.append(f"Użytkownik '{line}' istnieje. Podaj hasło:")
                    self.current_state = self.STATE_PASSWORD
                else:
                    self.console_lines.append(f"Nie znaleziono '{line}'. Podaj swoje imię:")
                    self.current_state = self.STATE_REG_FIRST

            elif self.current_state == self.STATE_PASSWORD:
                username = self.temp_user["username"]
                if "password_attempts" not in self.temp_user:
                    self.temp_user["password_attempts"] = 0

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
                    self.check_tech_completion()
                else:
                    self.temp_user["password_attempts"] += 1
                    attempts_left = 5 - self.temp_user["password_attempts"]

                    if attempts_left <= 0:
                        self.console_lines.append("❌ Zbyt dużo błędnych prób hasła! Następuje blokada sesji.")
                        self.console_lines.append("--------------------------------------------")
                        self.console_lines.append("Podaj nazwę użytkownika (login):")
                        self.temp_user = {}
                        self.current_state = self.STATE_USERNAME
                    else:
                        self.console_lines.append(f"Błędne hasło! Pozostało prób: {attempts_left}. Podaj hasło ponownie:")

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
                self.console_lines.append("Konto utworzone pomyślnie!")
                print_next_available_task(self.tasks, self.user_data, self.console_lines)
                self.current_state = self.STATE_CONSOLE
                self.check_tech_completion()

            elif self.current_state == self.STATE_SELECT_TECH:
                if line.isdigit():
                    idx = int(line) - 1
                    if 0 <= idx < len(self.available_techs_to_pick):
                        chosen_tech = self.available_techs_to_pick[idx]
                        cost = chosen_tech.get("cost", 0)
                        current_sp = self.user_data.get("science_points", 0)

                        if current_sp >= cost:
                            self.user_data["science_points"] -= cost
                            if "unlocked_techs" not in self.user_data:
                                self.user_data["unlocked_techs"] = []
                            self.user_data["unlocked_techs"].append(chosen_tech["id"])
                            self.manager.save_user_state(self.user_data)

                            max_sp = sum(t.get("reward_sp", 1) for t in self.tasks)
                            self.console_lines.append(f"> {line}")
                            self.console_lines.append(f"⭐ Odblokowano technologię: {chosen_tech['name']}! (-{cost} SP)")
                            self.console_lines.append(f"Punkty SP: {self.user_data['science_points']} / {max_sp}")
                            print_next_available_task(self.tasks, self.user_data, self.console_lines)
                            self.current_state = self.STATE_CONSOLE
                        else:
                            self.console_lines.append(f"❌ Za mało punktów SP! Potrzebujesz {cost} SP, masz {current_sp} SP.")
                    else:
                        self.console_lines.append(f"Błędny numer! Wybierz spośród dostępnych (1-{len(self.available_techs_to_pick)}):")
                else:
                    self.console_lines.append("Wpisz numer technologii!")

            elif self.current_state == self.STATE_CONFIRM_RESET:
                self.console_lines.append(f"> {line}")
                if line.upper() in ["T", "TAK", "Y", "YES"]:
                    if self.user_data and "username" in self.user_data:
                        self.manager.delete_user(self.user_data["username"])
                    self.console_lines.append("🗑️ Zresetowano dane. Podaj login:")
                    self.user_data = None
                    self.temp_user = {}
                    self.current_state = self.STATE_USERNAME
                else:
                    self.console_lines.append("Anulowano.")
                    self.current_state = self.STATE_CONSOLE

            # --- GŁÓWNA KONSOLA BASIC ---
            elif self.current_state == self.STATE_CONSOLE:
                # Szybkie pomijanie zadań do testów pod cyfrą '1' lub komendą '_SKIP'
                if line == "1" or line.upper() == "_SKIP":
                    unlocked_techs = set(self.user_data.get("unlocked_techs", []))
                    current_task = None

                    # Szukamy pierwszego aktywnego nieukończonego zadania
                    for task in self.tasks:
                        tech_id = task.get("tech_id")
                        if tech_id in unlocked_techs and task["id"] not in self.user_data["completed_tasks"]:
                            current_task = task
                            break

                    if current_task:
                        reward = current_task.get("reward_sp", 1)
                        self.user_data["science_points"] += reward
                        self.user_data["completed_tasks"].append(current_task["id"])

                        max_sp = sum(t.get("reward_sp", 1) for t in self.tasks)
                        self.console_lines.append("⏩ [DEBUG] POMINIĘTO ZADANIE!")
                        self.console_lines.append(f"✅ ZADANIE ZALICZONE! (+{reward} SP)")
                        self.console_lines.append(f"Punkty SP: {self.user_data['science_points']} / {max_sp}")
                        self.manager.save_user_state(self.user_data)

                        print_next_available_task(self.tasks, self.user_data, self.console_lines)
                        self.check_tech_completion()
                    else:
                        self.console_lines.append("⏩ [DEBUG] Brak aktywnych zadań do pominięcia.")
                    return True

                # Wciśnięcie samego ENTER daje pustą linię
                if not line:
                    self.console_lines.append("")
                    return True

                self.console_lines.append(f"KOK-BASIC> {line}")

                if line.upper() == "EXIT":
                    self.manager.save_user_state(self.user_data)
                    return False

                if line.upper() == "_RESET":
                    self.console_lines.append("⚠️ UWAGA: Czy na pewno chcesz usunąć profil? (T/N)")
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
                    unlocked_techs = set(self.user_data.get("unlocked_techs", []))

                    for task in self.tasks:
                        task_id = task["id"]
                        tech_id = task.get("tech_id")

                        if tech_id not in unlocked_techs or task_id in self.user_data["completed_tasks"]:
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
                        self.check_tech_completion()
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
            elif "HURA" in line or "⭐" in line:
                color = (255, 105, 180)
            elif line.startswith("⚠️") or line.startswith("🗑️") or "SYNTAX ERROR" in line or line.startswith("❌"):
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
        elif self.current_state == self.STATE_SELECT_TECH:
            prompt_symbol = "WYBIERZ TECH> "
            
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
