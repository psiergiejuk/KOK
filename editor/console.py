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

        for f in [523.25, 659.25, 783.99, 1046.50]:
            s = make_tone(f, 0.08)
            s.play()
            pygame.time.delay(70)
    except Exception:
        pass

def wrap_text(text: str, font, max_width: int) -> list[str]:
    """Dzieli długi tekst na linijki tak, aby zmieścił się w zadanej szerokości w pikselach."""
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        test_line = " ".join(current_line + [word])
        try:
            w = font.size(test_line)[0]
        except Exception:
            w = len(test_line) * 10
        if w <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []
    if current_line:
        lines.append(" ".join(current_line))
    return lines

def print_next_available_task(tasks, user_data, console_lines):
    """Zachowane dla kompatybilności wstecznej (zadania prezentowane są w dymku)."""
    pass

class RetroConsoleManager:
    def __init__(self, font):
        self.font = font
        try:
            self.hud_font = pygame.font.SysFont("Courier New", 16)
        except Exception:
            self.hud_font = font

        try:
            self.bubble_font = pygame.font.SysFont("Courier New", 14)
        except Exception:
            self.bubble_font = font

        self.bubble_visible = True
        self.bubble_notification = None

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
                        tech_data["task_ids"] = [t["id"] for t in tech_tasks]

                        for t in tech_tasks:
                            t["tech_id"] = tech_data["id"]
                            self.tasks.append(t)
                        self.technologies.append(tech_data)
        except Exception as e:
            print(f"Błąd ładowania konfiguracji technologii: {e}")

    def get_current_active_task(self):
        """Zwraca pierwsze nieukończone zadanie z odblokowanych technologii."""
        if not self.user_data:
            return None
        unlocked = set(self.user_data.get("unlocked_techs", []))
        completed = set(self.user_data.get("completed_tasks", []))
        for task in self.tasks:
            tech_id = task.get("tech_id")
            if tech_id in unlocked and task["id"] not in completed:
                return task
        return None

    def get_active_tech_info(self):
        """Zwraca (active_tech_id, tech_sp_earned, tech_total_sp) dla aktualnie aktywnej technologii."""
        if not self.user_data:
            return "PRINT_1", 0, 5

        current_task = self.get_current_active_task()
        if current_task:
            active_tech_id = current_task.get("tech_id")
        else:
            unlocked = self.user_data.get("unlocked_techs", [])
            active_tech_id = unlocked[-1] if unlocked else "PRINT_1"

        tech_tasks = [t for t in self.tasks if t.get("tech_id") == active_tech_id]
        tech_total_sp = sum(t.get("reward_sp", 1) for t in tech_tasks) if tech_tasks else 5
        completed = set(self.user_data.get("completed_tasks", []))
        tech_sp_earned = sum(t.get("reward_sp", 1) for t in tech_tasks if t["id"] in completed)
        return active_tech_id, tech_sp_earned, tech_total_sp

    def show_bubble_notification(self, title: str, message: str, duration_frames: int = 150):
        self.bubble_notification = {
            "title": title,
            "message": message,
            "timer": duration_frames
        }

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
        if event.key in [pygame.K_F1,]:
            self.bubble_visible = not self.bubble_visible
            return True

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
                    if self.user_data.get("exit_task_pending"):
                        self.user_data["exit_task_pending"] = False
                        if "exit_task" not in self.user_data.get("completed_tasks", []):
                            reward = 5
                            self.user_data.setdefault("completed_tasks", []).append("exit_task")
                            self.user_data["science_points"] = self.user_data.get("science_points", 0) + reward
                            self.manager.save_user_state(self.user_data)
                            play_retro_victory_sound()
                            self.show_bubble_notification(
                                "🎉 BRAWO! (+5 SP)",
                                "Wróciłeś do KOK BASIC!\nZadanie EXIT zaliczone!"
                            )

                    self.console_lines.append(f"Zalogowano pomyślnie! Witaj, {self.user_data['first_name']}.")
                    unlocked = self.user_data.get('unlocked_techs', [])
                    self.console_lines.append(f"Odblokowane technologie: {', '.join(unlocked) if unlocked else 'Brak'}")
                    _, tech_sp_earned, tech_total_sp = self.get_active_tech_info()
                    self.console_lines.append(f"Punkty SP: {tech_sp_earned} / {tech_total_sp}")
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
                _, tech_sp_earned, tech_total_sp = self.get_active_tech_info()
                self.console_lines.append(f"Punkty SP: {tech_sp_earned} / {tech_total_sp}")
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

                            _, tech_sp_earned, tech_total_sp = self.get_active_tech_info()
                            self.console_lines.append(f"> {line}")
                            self.console_lines.append(f"⭐ Odblokowano technologię: {chosen_tech['name']}! (-{cost} SP)")
                            self.console_lines.append(f"Punkty SP: {tech_sp_earned} / {tech_total_sp}")
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
                if line == "1" or line.upper() == "_SKIP":
                    current_task = self.get_current_active_task()
                    if current_task:
                        reward = current_task.get("reward_sp", 1)
                        self.user_data["science_points"] = self.user_data.get("science_points", 0) + reward
                        self.user_data.setdefault("completed_tasks", []).append(current_task["id"])

                        _, tech_sp_earned, tech_total_sp = self.get_active_tech_info()
                        self.manager.save_user_state(self.user_data)
                        play_retro_victory_sound()
                        self.show_bubble_notification(
                            f"⏩ POMINIĘTO (+{reward} SP)",
                            f"Zadanie zaliczone!\nSP: {tech_sp_earned} / {tech_total_sp}"
                        )
                        self.check_tech_completion()
                    else:
                        self.show_bubble_notification("⏩ DEBUG", "Brak zadań do pominięcia.")
                    return True

                if not line:
                    self.console_lines.append("")
                    return True

                self.console_lines.append(f"KOK-BASIC> {line}")

                if line.upper() == "EXIT":
                    current_task = self.get_current_active_task()
                    if current_task and current_task["id"] == "exit_task":
                        self.user_data["exit_task_pending"] = True
                    self.manager.save_user_state(self.user_data)
                    return False

                if line.upper() == "_RESET":
                    self.console_lines.append("⚠️ UWAGA: Czy na pewno chcesz usunąć profil? (T/N)")
                    self.current_state = self.STATE_CONFIRM_RESET
                    return True

                variables = self.user_data.setdefault("variables", {}) if self.user_data else None
                found, success = self.command_registry.execute_command(line, self.console_lines, variables)

                if not found:
                    self.console_lines.append(f"SYNTAX ERROR: Nieznana komenda '{line.split()[0]}'")
                    return True

                if success:
                    cmd_name = line.split()[0].upper()
                    if "=" in cmd_name and not cmd_name.startswith("LET"):
                        cmd_name = cmd_name.split("=")[0].strip()
                    if "action_counts" not in self.user_data:
                        self.user_data["action_counts"] = {}
                    self.user_data["action_counts"][cmd_name] = self.user_data["action_counts"].get(cmd_name, 0) + 1

                    task_completed_now = False
                    current_task = self.get_current_active_task()

                    if current_task and QuestValidator.validate(current_task, line, self.user_data):
                        task_id = current_task["id"]
                        reward = current_task.get("reward_sp", 1)
                        self.user_data["science_points"] = self.user_data.get("science_points", 0) + reward
                        self.user_data.setdefault("completed_tasks", []).append(task_id)

                        _, tech_sp_earned, tech_total_sp = self.get_active_tech_info()
                        self.manager.save_user_state(self.user_data)
                        play_retro_victory_sound()
                        self.show_bubble_notification(
                            f"🌟 BRAWO! (+{reward} SP)",
                            f"Zadanie zaliczone!\nSP: {tech_sp_earned} / {tech_total_sp}"
                        )
                        task_completed_now = True

                    if task_completed_now:
                        self.check_tech_completion()
        else:
            if hasattr(event, "unicode") and event.unicode and event.unicode.isprintable():
                self.input_text = self.input_text[:self.cursor_pos] + event.unicode + self.input_text[self.cursor_pos:]
                self.cursor_pos += 1
        return True

    def draw(self, screen, width, height):
        # 1. Tło obudowy monitora (retro szaro-beżowy plastik z lat 80.)
        screen.fill((190, 185, 170))

        # 2. Definicja ekranu kineskopu (CRT Viewport z zaokrąglonymi rogami)
        margin_x = 70
        margin_top = 50
        panel_height = 70  # Miejsce na dolny panel z diodami i logo
        screen_w = width - (margin_x * 2)
        screen_h = height - margin_top - panel_height - 30

        crt_rect = pygame.Rect(margin_x, margin_top, screen_w, screen_h)
        
        # Tworzymy powierzchnię dla zawartości ekranu CRT
        crt_surf = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
        crt_surf.fill((10, 20, 10))  # Ciemnozielone/czarne tło fosforowe

        # --- DYSKRETNY PASEK STATUSU (HUD) W WEWNĄTRZ KINESKOPU ---
        hud_height = 30
        pygame.draw.rect(crt_surf, (15, 30, 15), (0, 0, screen_w, hud_height))
        pygame.draw.line(crt_surf, (40, 80, 40), (0, hud_height), (screen_w, hud_height), 1)

        if self.user_data and self.current_state == self.STATE_CONSOLE:
            active_task = self.get_current_active_task()
            mission_text = f"🎯 MISJA: {active_task['title']}" if active_task else "🎉 ZADANIA ZALICZONE!"
            _, tech_sp_earned, tech_total_sp = self.get_active_tech_info()
            sp_text = f"⭐ SP: {tech_sp_earned}/{tech_total_sp} | {self.user_data.get('first_name', '')}"

            mission_surf = self.hud_font.render(mission_text, True, (0, 255, 120))
            sp_surf = self.hud_font.render(sp_text, True, (0, 220, 255))

            crt_surf.blit(mission_surf, (15, 6))
            crt_surf.blit(sp_surf, (max(screen_w - sp_surf.get_width() - 15, 250), 6))
        else:
            logo_surf = self.hud_font.render("KOK BASIC - Retro Emulator Edukacyjny", True, (0, 200, 100))
            crt_surf.blit(logo_surf, (15, 6))

        # --- LINIE TEKSTU KONSOLI ---
        line_height = 24
        max_lines = (screen_h - hud_height - 60) // line_height
        visible_lines = self.console_lines[-max_lines:]
        num_lines = len(visible_lines)
        bottom_limit = screen_h - 45
        start_y = bottom_limit - (num_lines * line_height)
        y_offset = max(hud_height + 10, start_y)
        
        for line in visible_lines:
            if "HURA" in line or "⭐" in line:
                color = (255, 100, 200)
            elif line.startswith("⚠️") or "SYNTAX ERROR" in line or line.startswith("❌"):
                color = (255, 80, 80)
            elif "✅" in line or "Zalogowano" in line or "BRAWO" in line:
                color = (80, 255, 80)
            else:
                color = (150, 255, 150)  # Klasyczny zielony fosfor CRT
                
            text_surface = self.font.render(line, True, color)
            crt_surf.blit(text_surface, (20, y_offset))
            y_offset += line_height

        # --- DYMEK MISJI (F1) ---
        if self.user_data and self.current_state == self.STATE_CONSOLE:
            if not self.bubble_visible:
                badge_text = "[F1] Pokaż misję 💬"
                badge_surf = self.bubble_font.render(badge_text, True, (150, 255, 150))
                bx = screen_w - badge_surf.get_width() - 20
                by = hud_height + 10
                bg_rect = (bx - 8, by - 3, badge_surf.get_width() + 16, badge_surf.get_height() + 6)
                pygame.draw.rect(crt_surf, (10, 40, 20), bg_rect, border_radius=4)
                pygame.draw.rect(crt_surf, (50, 150, 80), bg_rect, width=1, border_radius=4)
                crt_surf.blit(badge_surf, (bx, by))
            else:
                bubble_width = 320
                bubble_x = screen_w - bubble_width - 20
                bubble_y = hud_height + 10

                if self.bubble_notification and self.bubble_notification.get("timer", 0) > 0:
                    self.bubble_notification["timer"] -= 1
                    header_text = self.bubble_notification["title"]
                    header_color = (100, 255, 150)
                    body_raw = self.bubble_notification["message"]
                else:
                    active_task = self.get_current_active_task()
                    if active_task:
                        header_text = f"💬 {active_task['title']}"
                        header_color = (255, 220, 50)
                        body_raw = active_task.get("instruction", "")
                    else:
                        header_text = "🎉 POZIOM UKOŃCZONY!"
                        header_color = (255, 100, 200)
                        body_raw = "Wszystkie zadania ukończone."

                body_lines = []
                for paragraph in body_raw.split("\n"):
                    body_lines.extend(wrap_text(paragraph, self.bubble_font, bubble_width - 24))

                line_h = 18
                title_surf = self.bubble_font.render(header_text, True, header_color)
                content_h = 12 + title_surf.get_height() + 6 + (len(body_lines) * line_h) + 20
                
                bubble_surf = pygame.Surface((bubble_width, content_h), pygame.SRCALPHA)
                pygame.draw.rect(bubble_surf, (10, 25, 15, 240), (0, 0, bubble_width, content_h), border_radius=6)
                pygame.draw.rect(bubble_surf, (60, 180, 90), (0, 0, bubble_width, content_h), width=1, border_radius=6)

                bubble_surf.blit(title_surf, (12, 8))
                div_y = 8 + title_surf.get_height() + 4
                pygame.draw.line(bubble_surf, (40, 100, 60), (12, div_y), (bubble_width - 12, div_y), 1)

                curr_y = div_y + 6
                for bl in body_lines:
                    b_surf = self.bubble_font.render(bl, True, (200, 240, 200))
                    bubble_surf.blit(b_surf, (12, curr_y))
                    curr_y += line_h

                hint_surf = self.bubble_font.render("[F1] Schowaj", True, (100, 140, 110))
                bubble_surf.blit(hint_surf, (bubble_width - hint_surf.get_width() - 12, content_h - 18))

                crt_surf.blit(bubble_surf, (bubble_x, bubble_y))

        # --- LINIA INPUTU I KURSOR ---
        prompt_symbol = "KOK-BASIC> " if self.current_state == self.STATE_CONSOLE else ">> "
        if self.current_state == self.STATE_CONFIRM_RESET:
            prompt_symbol = "RESET (T/N)> "
        elif self.current_state == self.STATE_SELECT_TECH:
            prompt_symbol = "WYBIERZ TECH> "
            
        display_text = "*" * len(self.input_text) if self.current_state in [self.STATE_PASSWORD, self.STATE_REG_PASS] else self.input_text

        text_left = display_text[:self.cursor_pos]
        text_right = display_text[self.cursor_pos:]

        x_cursor_pos = 20
        prompt_surf = self.font.render(prompt_symbol, True, (100, 255, 100))
        crt_surf.blit(prompt_surf, (x_cursor_pos, screen_h - 35))
        x_cursor_pos += prompt_surf.get_width()

        if text_left:
            left_surf = self.font.render(text_left, True, (150, 255, 150))
            crt_surf.blit(left_surf, (x_cursor_pos, screen_h - 35))
            x_cursor_pos += left_surf.get_width()

        cursor_surf = self.font.render("_", True, (150, 255, 150))
        crt_surf.blit(cursor_surf, (x_cursor_pos, screen_h - 35))
        x_cursor_pos += cursor_surf.get_width()

        if text_right:
            right_surf = self.font.render(text_right, True, (150, 255, 150))
            crt_surf.blit(right_surf, (x_cursor_pos, screen_h - 35))

        # --- SCANLINES (PASKI SKANOWANIA) ---
        scanline_surf = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
        for y in range(0, screen_h, 3):
            pygame.draw.line(scanline_surf, (0, 0, 0, 60), (0, y), (screen_w, y), 1)
        crt_surf.blit(scanline_surf, (0, 0))

        # ========================================================
        # --- FIZYCZNE ZAOKRĄGLENIE RANTÓW KINESKOPU (MASKA) ---
        # ========================================================
        corner_radius = 18
        mask_surf = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
        mask_surf.fill((0, 0, 0, 0))
        pygame.draw.rect(mask_surf, (255, 255, 255, 255), (0, 0, screen_w, screen_h), border_radius=corner_radius)
        crt_surf.blit(mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

        # Rysujemy zaokrąglony ekran na głównym oknie obudowy
        screen.blit(crt_surf, (margin_x, margin_top))

        # Gruba czarna ramka wnęki kineskopu z zaokrąglonymi rogami
        pygame.draw.rect(screen, (30, 30, 30), crt_rect, width=6, border_radius=corner_radius)
        pygame.draw.rect(screen, (10, 10, 10), crt_rect, width=2, border_radius=corner_radius)

        # ==========================================
        # --- DOLNY PANEL OBUDOWY Z DIODAMI I LOGO ---
        # ==========================================
        panel_y = margin_top + screen_h + 10
        
        # Wgłębienie panelu sterowania
        pygame.draw.rect(screen, (160, 155, 140), (margin_x, panel_y, screen_w, panel_height - 10), border_radius=6)
        pygame.draw.rect(screen, (120, 115, 105), (margin_x, panel_y, screen_w, panel_height - 10), width=2, border_radius=6)

        # Napis na obudowie
        model_font = pygame.font.SysFont("Courier New", 14, bold=True)
        brand_surf = model_font.render("KOK-88 EDUCATIONAL MICROCOMPUTER", True, (70, 65, 60))
        screen.blit(brand_surf, (margin_x + 20, panel_y + 12))

        # --- SEKCJA DIOD LED (STATUSOWE + GPIO DLA I/O) ---
        led_start_x = margin_x + 360
        led_y = panel_y + 15

        main_leds = [
            ("PWR", (0, 230, 0), True),
            ("DISK", (230, 40, 40), False),
            ("SYNC", (230, 200, 0), True)
        ]

        curr_lx = led_start_x
        for label, color, is_on in main_leds:
            lbl_surf = model_font.render(label, True, (80, 75, 70))
            screen.blit(lbl_surf, (curr_lx, led_y + 16))
            
            pygame.draw.circle(screen, (90, 85, 80), (curr_lx + 12, led_y + 8), 7)
            led_color = color if is_on else (40, 40, 40)
            pygame.draw.circle(screen, led_color, (curr_lx + 12, led_y + 8), 5)
            if is_on:
                pygame.draw.circle(screen, (255, 255, 255), (curr_lx + 10, led_y + 6), 2)
            curr_lx += 55

        gpio_label = model_font.render("GPIO I/O:", True, (70, 65, 60))
        screen.blit(gpio_label, (curr_lx + 10, led_y + 16))
        curr_lx += 85

        for i in range(8):
            gpio_on = (i == 0 or i == 3) 
            g_color = (0, 200, 255) if gpio_on else (40, 40, 40)
            
            pygame.draw.circle(screen, (90, 85, 80), (curr_lx + 8, led_y + 8), 5)
            pygame.draw.circle(screen, g_color, (curr_lx + 8, led_y + 8), 3)
            
            num_surf = pygame.font.SysFont("Arial", 9).render(str(i), True, (90, 85, 80))
            screen.blit(num_surf, (curr_lx + 5, led_y + 16))
            
            curr_lx += 22
