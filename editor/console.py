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

def play_retro_fail_sound():
    """Generuje i odtwarza retro dźwięk porażki w stylu Mario/Pegasusa (opadające tony)."""
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=22050, size=-16, channels=1)
        sample_rate = 22050
        def make_tone(freq, duration):
            num_samples = int(sample_rate * duration)
            buf = array.array('h', [int(32767 * 0.3 * math.sin(2 * math.pi * freq * i / sample_rate)) for i in range(num_samples)])
            return pygame.mixer.Sound(buffer=buf)

        for f, d in [(493.88, 0.09), (466.16, 0.09), (440.00, 0.09), (392.00, 0.14), (311.13, 0.22)]:
            s = make_tone(f, d)
            s.play()
            pygame.time.delay(int(d * 900))
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
            self.hud_font = pygame.font.SysFont("Courier New", 19, bold=True)
        except Exception:
            self.hud_font = font

        try:
            self.bubble_font = pygame.font.SysFont("Courier New", 20)
        except Exception:
            self.bubble_font = font

        try:
            self.bubble_title_font = pygame.font.SysFont("Courier New", 21, bold=True)
        except Exception:
            self.bubble_title_font = self.bubble_font

        try:
            self.model_font = pygame.font.SysFont("Courier New", 14, bold=True)
        except Exception:
            self.model_font = font

        try:
            self.gpio_num_font = pygame.font.SysFont("Arial", 9)
        except Exception:
            self.gpio_num_font = font

        # Cache powierzchni CRT (tworzone raz dla danej rozdzielczości)
        self._crt_cache_size = None
        self._crt_surf = None
        self._scanline_surf = None
        self._mask_surf = None
        self._glass_overlay_surf = None
        self._chassis_surf = None

        # Stan paska podpowiedzi TAB (styl iPhone)
        self.tab_active = False
        self.tab_suggestions = []
        self.tab_selected_index = 0
        self.tab_prefix = ""

        # Stan diod LED na obudowie
        self.disk_led_timer = 0
        self.gpio_pins = [True, False, False, True, False, False, False, False]

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
        self.STATE_QUIZ = "QUIZ"

        self.current_state = self.STATE_USERNAME
        self.input_text = ""
        self.cursor_pos = 0
        self.temp_user = {}
        self.user_data = None
        self.available_techs_to_pick = []
        self.active_quiz = None
        self.command_history = []
        self.history_index = None

        self.console_lines = [
            "WITAJ W MINIMALISTYCZNYM EMULATORZE KOK BASIC",
            "--------------------------------------------",
            "Podaj nazwę użytkownika (login):"
        ]

        self.tasks = []
        self.quizzes = []
        self.technologies = []
        try:
            with open("config/tech_tree.json", "r", encoding="utf-8") as f:
                root_cfg = json.load(f)
                tech_files = root_cfg.get("technologies_files", [])

                for file_path in tech_files:
                    with open(file_path, "r", encoding="utf-8") as tf:
                        tech_data = json.load(tf)
                        tech_tasks = tech_data.pop("tasks", [])
                        tech_quizzes = tech_data.pop("quizzes", [])
                        tech_data["task_ids"] = [t["id"] for t in tech_tasks]
                        tech_data["quiz_ids"] = [q["id"] for q in tech_quizzes]

                        for t in tech_tasks:
                            t["tech_id"] = tech_data["id"]
                            self.tasks.append(t)
                        for q in tech_quizzes:
                            q["tech_id"] = tech_data["id"]
                            self.quizzes.append(q)
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

    def get_available_quizzes(self) -> list[dict]:
        """Zwraca listę nierozwiązanych quizów z odblokowanych technologii."""
        if not self.user_data:
            return []
        unlocked = set(self.user_data.get("unlocked_techs", []))
        completed_q = set(self.user_data.get("completed_quizzes", []))
        return [q for q in self.quizzes if q.get("tech_id") in unlocked and q["id"] not in completed_q]

    def get_active_tech_info(self):
        """Zwraca (active_tech_id, tech_sp_earned, tech_total_sp) dla aktualnie aktywnej technologii."""
        if not self.user_data:
            return "HELP_1", 0, 5

        current_task = self.get_current_active_task()
        if current_task:
            active_tech_id = current_task.get("tech_id")
        else:
            unlocked = self.user_data.get("unlocked_techs", [])
            active_tech_id = unlocked[-1] if unlocked else "HELP_1"

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

    def is_tech_unlocked(self, tech_id: str) -> bool:
        """Sprawdza czy dana technologia jest już odblokowana przez gracza."""
        if not self.user_data:
            return False
        return tech_id in self.user_data.get("unlocked_techs", [])

    def get_unlocked_commands_for_tab(self) -> list[str]:
        """Zwraca listę komend dostępnych na pasku TAB na podstawie odblokowanych technologii."""
        unlocked = set(self.user_data.get("unlocked_techs", [])) if self.user_data else set()
        cmds = ["HELP", "PRINT", "QUIZ"]
        if "CLS_1" in unlocked:
            cmds.append("CLS")
        if "HISTORY_1" in unlocked:
            cmds.append("HISTORY")
        if any(t in unlocked for t in ["VAR_STR", "VAR_INT", "VAR_FLOAT", "VAR_BOOL"]):
            cmds.append("LET")
        if "FOR_1" in unlocked:
            cmds.append("FOR")
        if "EXIT_1" in unlocked:
            cmds.append("EXIT")
        return cmds

    def check_tech_completion(self):
        """Sprawdza, czy gracz ukończył wszystkie zadania ORAZ quizy dla aktywnej technologii i może kupić kolejną."""
        completed = set(self.user_data.get("completed_tasks", []))
        completed_quizzes = set(self.user_data.get("completed_quizzes", []))
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
                        for qid in req_tech.get("quiz_ids", []):
                            if qid not in completed_quizzes:
                                req_tasks_completed = False
                                break

                if req_tasks_completed:
                    self.available_techs_to_pick.append(tech)

        # Przechodzimy do wyboru nowej technologii tylko wtedy, gdy gracz ukończył bieżące zadania I quizy
        if (
            self.available_techs_to_pick
            and self.current_state == self.STATE_CONSOLE
            and self.get_current_active_task() is None
            and len(self.get_available_quizzes()) == 0
        ):
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
                self.disk_led_timer = 15
            return False

        elif event.key == pygame.K_LEFT:
            self.cursor_pos = max(0, self.cursor_pos - 1)
        elif event.key == pygame.K_RIGHT:
            self.cursor_pos = min(len(self.input_text), self.cursor_pos + 1)
        elif event.key == pygame.K_BACKSPACE:
            self.tab_active = False
            if self.cursor_pos > 0:
                self.input_text = self.input_text[:self.cursor_pos - 1] + self.input_text[self.cursor_pos:]
                self.cursor_pos -= 1
        elif event.key == pygame.K_DELETE:
            self.tab_active = False
            if self.cursor_pos < len(self.input_text):
                self.input_text = self.input_text[:self.cursor_pos] + self.input_text[self.cursor_pos + 1:]

        elif event.key == pygame.K_UP and self.current_state == self.STATE_CONSOLE:
            if not self.is_tech_unlocked("HISTORY_1"):
                return True
            self.tab_active = False
            if self.command_history:
                if self.history_index is None:
                    self.history_index = len(self.command_history) - 1
                else:
                    self.history_index = max(0, self.history_index - 1)
                self.input_text = self.command_history[self.history_index]
                self.cursor_pos = len(self.input_text)

        elif event.key == pygame.K_DOWN and self.current_state == self.STATE_CONSOLE:
            if not self.is_tech_unlocked("HISTORY_1"):
                return True
            self.tab_active = False
            if self.command_history and self.history_index is not None:
                if self.history_index < len(self.command_history) - 1:
                    self.history_index += 1
                    self.input_text = self.command_history[self.history_index]
                else:
                    self.history_index = None
                    self.input_text = ""
                self.cursor_pos = len(self.input_text)

        elif event.key == pygame.K_TAB and self.current_state == self.STATE_CONSOLE:
            if not self.is_tech_unlocked("TAB_1"):
                return True

            available_cmds = self.get_unlocked_commands_for_tab()
            if not self.tab_active:
                self.tab_prefix = self.input_text.strip().upper()
                if not self.tab_prefix or " " in self.tab_prefix:
                    self.tab_suggestions = available_cmds
                else:
                    matches = [c for c in available_cmds if c.startswith(self.tab_prefix)]
                    self.tab_suggestions = matches if matches else available_cmds
                self.tab_selected_index = 0
                self.tab_active = True
            else:
                if self.tab_suggestions:
                    self.tab_selected_index = (self.tab_selected_index + 1) % len(self.tab_suggestions)

            if self.tab_suggestions:
                chosen = self.tab_suggestions[self.tab_selected_index]
                self.input_text = chosen + " "
                self.cursor_pos = len(self.input_text)

            if self.user_data:
                self.user_data.setdefault("action_counts", {})
                self.user_data["action_counts"]["TAB"] = self.user_data["action_counts"].get("TAB", 0) + 1
                current_task = self.get_current_active_task()
                if current_task and QuestValidator.validate(current_task, "TAB", self.user_data):
                    task_id = current_task["id"]
                    reward = current_task.get("reward_sp", 1)
                    self.user_data["science_points"] = self.user_data.get("science_points", 0) + reward
                    self.user_data.setdefault("completed_tasks", []).append(task_id)
                    _, tech_sp_earned, tech_total_sp = self.get_active_tech_info()
                    self.manager.save_user_state(self.user_data)
                    self.disk_led_timer = 15
                    play_retro_victory_sound()
                    self.show_bubble_notification(
                        f"🌟 BRAWO! (+{reward} SP)",
                        f"Zadanie zaliczone!\nSP: {tech_sp_earned} / {tech_total_sp}"
                    )
                    self.check_tech_completion()

        elif event.key == pygame.K_RETURN:
            self.tab_active = False
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
                self.disk_led_timer = 15
                self.console_lines.append("> ****")

                if self.user_data:
                    if self.user_data.get("exit_task_pending"):
                        self.user_data["exit_task_pending"] = False
                        if "exit_task" not in self.user_data.get("completed_tasks", []):
                            reward = 5
                            self.user_data.setdefault("completed_tasks", []).append("exit_task")
                            self.user_data["science_points"] = self.user_data.get("science_points", 0) + reward
                            self.manager.save_user_state(self.user_data)
                            self.disk_led_timer = 15
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
                self.disk_led_timer = 15
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
                            self.disk_led_timer = 15

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

            elif self.current_state == self.STATE_QUIZ:
                self.console_lines.append(f"ODPOWIEDŹ (1-4)> {line}")
                if line.isdigit() and 1 <= int(line) <= 4 and self.active_quiz:
                    choice = int(line)
                    if choice == self.active_quiz.get("correct"):
                        self.user_data["science_points"] = self.user_data.get("science_points", 0) + 1
                        self.user_data.setdefault("completed_quizzes", []).append(self.active_quiz["id"])
                        self.manager.save_user_state(self.user_data)
                        self.disk_led_timer = 15
                        play_retro_victory_sound()
                        self.active_quiz = None
                        self.current_state = self.STATE_CONSOLE
                        remaining = len(self.get_available_quizzes())
                        self.console_lines.append(f"✅ BRAWO! Dobra odpowiedź! (+1 SP) | Pozostało quizów: {remaining}")
                        if remaining > 0:
                            self.show_bubble_notification(
                                "🌟 DOBRA ODPOWIEDŹ! (+1 SP)",
                                f"Super! Pozostało jeszcze quizów: {remaining}.\nWpisz ponownie QUIZ, aby odpowiedzieć na kolejne pytanie!"
                            )
                        else:
                            self.show_bubble_notification(
                                "🎉 QUIZY UKOŃCZONE!",
                                "Rozwiązałeś wszystkie quizy z tego poziomu!"
                            )
                            self.check_tech_completion()
                    else:
                        play_retro_fail_sound()
                        self.active_quiz = None
                        self.current_state = self.STATE_CONSOLE
                        self.console_lines.append("❌ Oj, to nie ta odpowiedź! Wpisz QUIZ i spróbuj jeszcze raz!")
                        self.show_bubble_notification(
                            "❌ SPRÓBUJ JESZCZE RAZ!",
                            "Niestety to nie ta odpowiedź!\nWpisz komendę QUIZ i spróbuj ponownie!"
                        )
                else:
                    self.console_lines.append("⚠️ Wpisz cyfrę od 1 do 4 i wciśnij ENTER!")

            # --- GŁÓWNA KONSOLA BASIC ---
            elif self.current_state == self.STATE_CONSOLE:
                if line == "1" or line.upper() == "_SKIP":
                    current_task = self.get_current_active_task()
                    avail_quizzes = self.get_available_quizzes()
                    if current_task:
                        reward = current_task.get("reward_sp", 1)
                        self.user_data["science_points"] = self.user_data.get("science_points", 0) + reward
                        self.user_data.setdefault("completed_tasks", []).append(current_task["id"])

                        _, tech_sp_earned, tech_total_sp = self.get_active_tech_info()
                        self.manager.save_user_state(self.user_data)
                        self.disk_led_timer = 15
                        play_retro_victory_sound()
                        self.show_bubble_notification(
                            f"⏩ POMINIĘTO (+{reward} SP)",
                            f"Zadanie zaliczone!\nSP: {tech_sp_earned} / {tech_total_sp}"
                        )
                        self.check_tech_completion()
                    elif avail_quizzes:
                        q = avail_quizzes[0]
                        self.user_data["science_points"] = self.user_data.get("science_points", 0) + 1
                        self.user_data.setdefault("completed_quizzes", []).append(q["id"])
                        self.manager.save_user_state(self.user_data)
                        self.disk_led_timer = 15
                        play_retro_victory_sound()
                        rem = len(self.get_available_quizzes())
                        self.show_bubble_notification(
                            "⏩ POMINIĘTO QUIZ (+1 SP)",
                            f"Quiz zaliczony! Pozostało quizów: {rem}"
                        )
                        self.check_tech_completion()
                    else:
                        self.show_bubble_notification("⏩ DEBUG", "Brak zadań i quizów do pominięcia.")
                    return True

                if not line:
                    self.console_lines.append("")
                    return True

                self.command_history.append(line)
                self.history_index = None
                self.console_lines.append(f"KOK-BASIC> {line}")

                if line.upper() == "QUIZ":
                    avail_quizzes = self.get_available_quizzes()
                    if not avail_quizzes:
                        self.console_lines.append("🎉 Wszystkie dostępne quizy masz już rozwiązane!")
                    else:
                        self.active_quiz = avail_quizzes[0]
                        self.current_state = self.STATE_QUIZ
                        self.console_lines.append("=== 🧠 PYTANIE QUIZOWE (+1 SP) ===")
                        self.console_lines.append(self.active_quiz["question"])
                        for idx, opt in enumerate(self.active_quiz["options"], 1):
                            self.console_lines.append(f"  [{idx}] {opt}")
                        self.console_lines.append("Wpisz numer odpowiedzi (1-4) i wciśnij ENTER:")
                    return True

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

                if line.split()[0].upper() == "HISTORY" and not self.is_tech_unlocked("HISTORY_1"):
                    self.console_lines.append("🔒 Komenda HISTORY nie jest jeszcze odblokowana!")
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
                        self.disk_led_timer = 15
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
                self.tab_active = False
                self.input_text = self.input_text[:self.cursor_pos] + event.unicode + self.input_text[self.cursor_pos:]
                self.cursor_pos += 1
        return True

    def _build_chassis_surface(self, width, height, margin_x, margin_top, screen_w, screen_h, panel_height, corner_radius):
        """Buduje realistyczną, trójwymiarową obudowę monitora CRT z lat 80."""
        surf = pygame.Surface((width, height))
        # Ciemne tło pokoju/biurka wokół obudowy monitora
        surf.fill((18, 20, 26))

        # 1. Zewnętrzna bryła obudowy monitora (z cieniem i fazowaniem 3D)
        outer_pad = 10
        body_rect = pygame.Rect(outer_pad, outer_pad, width - outer_pad * 2, height - outer_pad * 2)
        # Cień pod monitorem
        pygame.draw.rect(surf, (8, 10, 14), body_rect.move(0, 4), border_radius=26)
        # Baza obudowy (ciepły retro beż)
        pygame.draw.rect(surf, (192, 186, 170), body_rect, border_radius=24)

        # Górny jasny blik 3D (światło padające z góry)
        highlight_rect = pygame.Rect(outer_pad + 4, outer_pad + 2, width - (outer_pad + 4) * 2, 18)
        pygame.draw.rect(surf, (224, 218, 204), highlight_rect, border_radius=12)

        # Dolny cień krawędzi obudowy
        bottom_shadow_rect = pygame.Rect(outer_pad + 4, height - outer_pad - 14, width - (outer_pad + 4) * 2, 12)
        pygame.draw.rect(surf, (135, 128, 114), bottom_shadow_rect, border_radius=10)

        # Zewnętrzny obrys bryły
        pygame.draw.rect(surf, (110, 105, 92), body_rect, width=3, border_radius=24)

        # Boczne kratki wentylacyjne na obudowie (lewa i prawa strona)
        for vent_y in range(margin_top + 30, margin_top + screen_h - 30, 14):
            # Lewa kratka
            pygame.draw.line(surf, (115, 110, 98), (22, vent_y), (44, vent_y), 3)
            pygame.draw.line(surf, (215, 210, 196), (22, vent_y + 2), (44, vent_y + 2), 1)
            # Prawa kratka
            pygame.draw.line(surf, (115, 110, 98), (width - 44, vent_y), (width - 22, vent_y), 3)
            pygame.draw.line(surf, (215, 210, 196), (width - 44, vent_y + 2), (width - 22, vent_y + 2), 1)

        # 2. Głęboka, skośna wnęka kineskopu (3D Bezel z 4 trapezów)
        bevel = 22
        ix1, iy1 = margin_x, margin_top
        ix2, iy2 = margin_x + screen_w, margin_top + screen_h
        ox1, oy1 = ix1 - bevel, iy1 - bevel
        ox2, oy2 = ix2 + bevel, iy2 + bevel

        # Górny skos (najciemniejszy – skierowany w dół, w cieniu)
        pygame.draw.polygon(surf, (132, 126, 112), [(ox1, oy1), (ox2, oy1), (ix2, iy1), (ix1, iy1)])
        # Lewy skos (średnio oświetlony)
        pygame.draw.polygon(surf, (172, 166, 152), [(ox1, oy1), (ix1, iy1), (ix1, iy2), (ox1, oy2)])
        # Prawy skos (lekko zacieniony)
        pygame.draw.polygon(surf, (152, 146, 132), [(ix2, iy1), (ox2, oy1), (ox2, oy2), (ix2, iy2)])
        # Dolny skos (najjaśniejszy – odbija światło z góry)
        pygame.draw.polygon(surf, (216, 210, 195), [(ix1, iy2), (ix2, iy2), (ox2, oy2), (ox1, oy2)])

        # Linie łączenia skosów w narożnikach wnęki
        for p_out, p_in in [((ox1, oy1), (ix1, iy1)), ((ox2, oy1), (ix2, iy1)), ((ox1, oy2), (ix1, iy2)), ((ox2, oy2), (ix2, iy2))]:
            pygame.draw.line(surf, (115, 110, 98), p_out, p_in, 2)

        # Krawędź zewnętrzna wnęki (wklęsły frez)
        outer_bezel_rect = pygame.Rect(ox1, oy1, ox2 - ox1, oy2 - oy1)
        pygame.draw.rect(surf, (110, 105, 94), outer_bezel_rect, width=2, border_radius=8)
        pygame.draw.line(surf, (225, 220, 206), (ox1 + 4, oy2 + 1), (ox2 - 4, oy2 + 1), 2)

        # 3. Dolny panel sterowania (wypukła listwa z grawerowanym rowkiem)
        panel_y = oy2 + 8
        panel_h = panel_height - 12
        panel_rect = pygame.Rect(ox1, panel_y, ox2 - ox1, panel_h)

        # Cień i wypełnienie panelu
        pygame.draw.rect(surf, (125, 120, 108), panel_rect.move(0, 2), border_radius=8)
        pygame.draw.rect(surf, (174, 168, 154), panel_rect, border_radius=8)
        # Fazowanie 3D panelu (jasna góra, ciemny dół)
        pygame.draw.line(surf, (215, 210, 196), (ox1 + 6, panel_y + 1), (ox2 - 6, panel_y + 1), 2)
        pygame.draw.rect(surf, (115, 110, 98), panel_rect, width=2, border_radius=8)

        # Metalowa tabliczka znamionowa z nitami dla napisu "KOK-88"
        badge_rect = pygame.Rect(margin_x + 10, panel_y + 8, 315, panel_h - 16)
        pygame.draw.rect(surf, (45, 42, 38), badge_rect, border_radius=4)
        pygame.draw.rect(surf, (130, 125, 112), badge_rect, width=1, border_radius=4)
        # 4 nity w rogach tabliczki
        for rx, ry in [
            (badge_rect.left + 5, badge_rect.top + 5),
            (badge_rect.right - 5, badge_rect.top + 5),
            (badge_rect.left + 5, badge_rect.bottom - 5),
            (badge_rect.right - 5, badge_rect.bottom - 5),
        ]:
            pygame.draw.circle(surf, (160, 155, 140), (rx, ry), 2)

        brand_surf = self.model_font.render("KOK-88 EDUCATIONAL MICROCOMPUTER", True, (220, 210, 185))
        surf.blit(brand_surf, (badge_rect.left + 16, badge_rect.centery - brand_surf.get_height() // 2))

        # Fizyczny przycisk zasilania (Power Switch 3D) po prawej stronie panelu
        pwr_btn_rect = pygame.Rect(ox2 - 58, panel_y + 8, 42, panel_h - 16)
        pygame.draw.rect(surf, (60, 58, 54), pwr_btn_rect.move(0, 2), border_radius=5)
        pygame.draw.rect(surf, (200, 75, 50), pwr_btn_rect, border_radius=5)
        pygame.draw.line(surf, (245, 130, 100), (pwr_btn_rect.left + 4, pwr_btn_rect.top + 2), (pwr_btn_rect.right - 4, pwr_btn_rect.top + 2), 2)
        pygame.draw.rect(surf, (90, 35, 25), pwr_btn_rect, width=2, border_radius=5)
        pwr_txt = self.gpio_num_font.render("I/O", True, (255, 235, 220))
        surf.blit(pwr_txt, (pwr_btn_rect.centerx - pwr_txt.get_width() // 2, pwr_btn_rect.centery - pwr_txt.get_height() // 2))

        return surf

    def draw(self, screen, width, height):
        # Definicja ekranu kineskopu (CRT Viewport z zaokrąglonymi rogami)
        margin_x = 70
        margin_top = 50
        panel_height = 70  # Miejsce na dolny panel z diodami i logo
        screen_w = width - (margin_x * 2)
        screen_h = height - margin_top - panel_height - 30

        crt_rect = pygame.Rect(margin_x, margin_top, screen_w, screen_h)
        corner_radius = 18

        # Inicjalizacja / odświeżenie cache'u powierzchni CRT oraz obudowy 3D tylko przy zmianie rozmiaru
        if self._crt_cache_size != (screen_w, screen_h):
            self._crt_cache_size = (screen_w, screen_h)
            self._crt_surf = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)

            self._scanline_surf = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
            for y in range(0, screen_h, 3):
                pygame.draw.line(self._scanline_surf, (0, 0, 0, 60), (0, y), (screen_w, y), 1)

            # Wypukłość szkła kineskopu: winieta krawędzi + delikatny odblask światła w rogu
            self._glass_overlay_surf = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
            for inset, alpha in [(0, 95), (3, 60), (7, 30), (12, 15)]:
                pygame.draw.rect(
                    self._glass_overlay_surf,
                    (0, 0, 0, alpha),
                    (inset, inset, screen_w - inset * 2, screen_h - inset * 2),
                    width=4,
                    border_radius=max(4, corner_radius - inset)
                )
            # Subtelny łukowaty blik szkła w lewym górnym narożniku kineskopu
            glare_poly = [
                (25, 14),
                (min(260, screen_w // 2), 14),
                (min(180, screen_w // 3), 55),
                (25, 95)
            ]
            pygame.draw.polygon(self._glass_overlay_surf, (255, 255, 255, 12), glare_poly)

            self._mask_surf = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
            self._mask_surf.fill((0, 0, 0, 0))
            pygame.draw.rect(self._mask_surf, (255, 255, 255, 255), (0, 0, screen_w, screen_h), border_radius=corner_radius)

            self._chassis_surf = self._build_chassis_surface(
                width, height, margin_x, margin_top, screen_w, screen_h, panel_height, corner_radius
            )

        # 1. Rysujemy trójwymiarową obudowę monitora z cache'u
        screen.blit(self._chassis_surf, (0, 0))

        crt_surf = self._crt_surf
        crt_surf.fill((10, 20, 10))  # Ciemnozielone/czarne tło fosforowe

        # --- DYSKRETNY PASEK STATUSU (HUD) W WEWNĄTRZ KINESKOPU ---
        hud_height = 30
        pygame.draw.rect(crt_surf, (15, 30, 15), (0, 0, screen_w, hud_height))
        pygame.draw.line(crt_surf, (40, 80, 40), (0, hud_height), (screen_w, hud_height), 1)

        if self.user_data and self.current_state in [self.STATE_CONSOLE, self.STATE_QUIZ]:
            active_task = self.get_current_active_task()
            avail_quizzes = self.get_available_quizzes()
            if active_task:
                mission_text = f"🎯 MISJA: {active_task['title']}"
            elif avail_quizzes:
                mission_text = f"🧠 QUIZ: Wpisz QUIZ (pozostało: {len(avail_quizzes)})"
            else:
                mission_text = "🎉 POZIOM UKOŃCZONY!"
            _, tech_sp_earned, tech_total_sp = self.get_active_tech_info()
            total_sp = self.user_data.get("science_points", 0)
            sp_text = f"⭐ SP: {total_sp} ({tech_sp_earned}/{tech_total_sp}) | 🧠 QUIZY: {len(avail_quizzes)} | {self.user_data.get('first_name', '')}"

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
        if self.user_data and self.current_state in [self.STATE_CONSOLE, self.STATE_QUIZ]:
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
                bubble_width = min(480, max(380, int(screen_w * 0.45)))
                bubble_x = screen_w - bubble_width - 20
                bubble_y = hud_height + 12

                if self.current_state == self.STATE_QUIZ and self.active_quiz:
                    header_text = "🧠 PYTANIE QUIZOWE (+1 SP)"
                    header_color = (80, 230, 255)
                    opts = "\n".join(f"[{i}] {o}" for i, o in enumerate(self.active_quiz["options"], 1))
                    body_raw = f"{self.active_quiz['question']}\n\n{opts}\n\nWpisz numer 1-4 i wciśnij ENTER!"
                elif self.bubble_notification and self.bubble_notification.get("timer", 0) > 0:
                    self.bubble_notification["timer"] -= 1
                    header_text = self.bubble_notification["title"]
                    header_color = (100, 255, 150)
                    body_raw = self.bubble_notification["message"]
                else:
                    active_task = self.get_current_active_task()
                    avail_quizzes = self.get_available_quizzes()
                    if active_task:
                        header_text = f"💬 {active_task['title']}"
                        header_color = (255, 220, 50)
                        body_raw = active_task.get("instruction", "")
                    elif avail_quizzes:
                        header_text = f"🧠 CZAS NA QUIZ! (Pozostało: {len(avail_quizzes)})"
                        header_color = (80, 230, 255)
                        body_raw = (
                            f"Brawo! Wykonałeś wszystkie ćwiczenia z tego poziomu!\n\n"
                            f"Aby przejść dalej, rozwiąż jeszcze {len(avail_quizzes)} "
                            f"pytania quizowe (+1 SP za każde).\n"
                            f"Wpisz komendę QUIZ i wciśnij ENTER!"
                        )
                    else:
                        header_text = "🎉 POZIOM UKOŃCZONY!"
                        header_color = (255, 100, 200)
                        body_raw = "Wszystkie zadania i quizy ukończone."

                title_lines = wrap_text(header_text, self.bubble_title_font, bubble_width - 28)
                body_lines = []
                for paragraph in body_raw.split("\n"):
                    body_lines.extend(wrap_text(paragraph, self.bubble_font, bubble_width - 28))

                title_line_h = 26
                line_h = 26
                title_block_h = len(title_lines) * title_line_h
                content_h = 16 + title_block_h + 10 + (len(body_lines) * line_h) + 32
                
                bubble_surf = pygame.Surface((bubble_width, content_h), pygame.SRCALPHA)
                pygame.draw.rect(bubble_surf, (10, 28, 16, 245), (0, 0, bubble_width, content_h), border_radius=8)
                pygame.draw.rect(bubble_surf, (80, 220, 110), (0, 0, bubble_width, content_h), width=2, border_radius=8)

                ty = 10
                for tl in title_lines:
                    t_surf = self.bubble_title_font.render(tl, True, header_color)
                    bubble_surf.blit(t_surf, (14, ty))
                    ty += title_line_h

                div_y = ty + 4
                pygame.draw.line(bubble_surf, (50, 130, 75), (14, div_y), (bubble_width - 14, div_y), 1)

                curr_y = div_y + 8
                for bl in body_lines:
                    b_surf = self.bubble_font.render(bl, True, (215, 255, 215))
                    bubble_surf.blit(b_surf, (14, curr_y))
                    curr_y += line_h

                hint_surf = self.bubble_font.render("[F1] Schowaj", True, (110, 165, 125))
                bubble_surf.blit(hint_surf, (bubble_width - hint_surf.get_width() - 14, content_h - 28))

                crt_surf.blit(bubble_surf, (bubble_x, bubble_y))

        # --- PASEK PODPOWIEDZI TAB (STYL IPHONE) ---
        if self.tab_active and self.tab_suggestions and self.current_state == self.STATE_CONSOLE:
            bar_y = screen_h - 68
            bar_x = 20
            hint_lbl = self.bubble_font.render("TAB ▸", True, (90, 180, 110))
            crt_surf.blit(hint_lbl, (bar_x, bar_y + 4))
            bar_x += hint_lbl.get_width() + 10

            for idx, cmd_name in enumerate(self.tab_suggestions):
                is_sel = (idx == self.tab_selected_index)
                chip_txt = f" {cmd_name} "
                txt_color = (10, 25, 10) if is_sel else (130, 230, 150)
                chip_surf = self.bubble_font.render(chip_txt, True, txt_color)
                chip_w = chip_surf.get_width() + 12
                chip_h = chip_surf.get_height() + 6
                chip_rect = (bar_x, bar_y, chip_w, chip_h)

                if is_sel:
                    pygame.draw.rect(crt_surf, (80, 255, 130), chip_rect, border_radius=6)
                    pygame.draw.rect(crt_surf, (200, 255, 210), chip_rect, width=1, border_radius=6)
                else:
                    pygame.draw.rect(crt_surf, (15, 45, 25), chip_rect, border_radius=6)
                    pygame.draw.rect(crt_surf, (50, 130, 70), chip_rect, width=1, border_radius=6)

                crt_surf.blit(chip_surf, (bar_x + 6, bar_y + 3))
                bar_x += chip_w + 8

        # --- LINIA INPUTU I KURSOR ---
        prompt_symbol = "KOK-BASIC> " if self.current_state == self.STATE_CONSOLE else ">> "
        if self.current_state == self.STATE_CONFIRM_RESET:
            prompt_symbol = "RESET (T/N)> "
        elif self.current_state == self.STATE_SELECT_TECH:
            prompt_symbol = "WYBIERZ TECH> "
        elif self.current_state == self.STATE_QUIZ:
            prompt_symbol = "ODPOWIEDŹ (1-4)> "
            
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

        # --- SCANLINES (PASKI SKANOWANIA) ORAZ WYPUKŁOŚĆ SZKŁA ---
        crt_surf.blit(self._scanline_surf, (0, 0))
        crt_surf.blit(self._glass_overlay_surf, (0, 0))

        # ========================================================
        # --- FIZYCZNE ZAOKRĄGLENIE RANTÓW KINESKOPU (MASKA) ---
        # ========================================================
        crt_surf.blit(self._mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

        # Rysujemy zaokrąglony ekran na głównym oknie obudowy
        screen.blit(crt_surf, (margin_x, margin_top))

        # Gumowa uszczelka i głęboka czarna ramka wokół szklanej bańki kineskopu
        pygame.draw.rect(screen, (38, 42, 38), crt_rect.inflate(4, 4), width=5, border_radius=corner_radius + 2)
        pygame.draw.rect(screen, (14, 16, 14), crt_rect, width=4, border_radius=corner_radius)
        pygame.draw.rect(screen, (30, 75, 40), crt_rect.inflate(-2, -2), width=1, border_radius=corner_radius)

        # ==========================================
        # --- SEKCJA DIOD LED NA DOLNYM PANELU 3D ---
        # ==========================================
        panel_y = margin_top + screen_h + 30
        led_start_x = margin_x + 350
        led_y = panel_y + 12

        if self.disk_led_timer > 0:
            self.disk_led_timer -= 1

        main_leds = [
            ("PWR", (0, 230, 60), True),
            ("DISK", (255, 50, 40), self.disk_led_timer > 0),
            ("SYNC", (240, 200, 20), True)
        ]

        curr_lx = led_start_x
        for label, color, is_on in main_leds:
            lbl_surf = self.model_font.render(label, True, (65, 60, 55))
            screen.blit(lbl_surf, (curr_lx, led_y + 16))
            
            # Metalowa oprawka diody 3D
            pygame.draw.circle(screen, (55, 52, 48), (curr_lx + 12, led_y + 7), 8)
            pygame.draw.circle(screen, (120, 115, 105), (curr_lx + 12, led_y + 8), 7, width=1)
            led_color = color if is_on else (35, 35, 35)
            pygame.draw.circle(screen, led_color, (curr_lx + 12, led_y + 7), 5)
            if is_on:
                pygame.draw.circle(screen, (255, 255, 255), (curr_lx + 10, led_y + 5), 2)
            curr_lx += 55

        gpio_label = self.model_font.render("GPIO I/O:", True, (65, 60, 55))
        screen.blit(gpio_label, (curr_lx + 10, led_y + 16))
        curr_lx += 85

        for i in range(8):
            gpio_on = bool(self.gpio_pins[i]) if i < len(self.gpio_pins) else False
            g_color = (0, 210, 255) if gpio_on else (35, 35, 35)
            
            pygame.draw.circle(screen, (55, 52, 48), (curr_lx + 8, led_y + 7), 6)
            pygame.draw.circle(screen, g_color, (curr_lx + 8, led_y + 7), 4)
            if gpio_on:
                pygame.draw.circle(screen, (220, 255, 255), (curr_lx + 7, led_y + 6), 1)
            
            num_surf = self.gpio_num_font.render(str(i), True, (65, 60, 55))
            screen.blit(num_surf, (curr_lx + 5, led_y + 16))
            
            curr_lx += 22
