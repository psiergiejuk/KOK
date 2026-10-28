import json
from datetime import datetime
import pygame
from core.user_manager import UserManager
from core.command_registry import CommandRegistry
from core.quest_validator import QuestValidator
from devices.display import (
    CRTChassisRenderer,
    RETRO_ICON_MAP,
    _RetroFontWrapper,
    play_retro_fail_sound,
    play_retro_victory_sound,
    sanitize_retro_text,
    wrap_text,
)
from editor.program_view import ProgramEditorView
from editor.tech_tree_view import TechMapView


def print_next_available_task(tasks, user_data, console_lines):
    """Zachowane dla kompatybilności wstecznej (zadania prezentowane są w dymku)."""
    pass


class RetroConsoleManager:
    def __init__(self, font, user_manager=None):
        self.font = _RetroFontWrapper(font)
        try:
            self.hud_font = _RetroFontWrapper(pygame.font.SysFont("Courier New", 19, bold=True))
        except Exception:
            self.hud_font = self.font

        try:
            self.bubble_font = _RetroFontWrapper(pygame.font.SysFont("Courier New", 20))
        except Exception:
            self.bubble_font = self.font

        try:
            self.bubble_title_font = _RetroFontWrapper(pygame.font.SysFont("Courier New", 21, bold=True))
        except Exception:
            self.bubble_title_font = self.bubble_font

        try:
            self.model_font = _RetroFontWrapper(pygame.font.SysFont("Courier New", 14, bold=True))
        except Exception:
            self.model_font = self.font

        try:
            self.gpio_num_font = _RetroFontWrapper(pygame.font.SysFont("Arial", 9))
        except Exception:
            self.gpio_num_font = self.font

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

        self.manager = user_manager or UserManager()
        self.command_registry = CommandRegistry()
        self.command_registry.on_pause = self._on_pause
        self.gpio_pins = self.command_registry.gpio_pins

        self.STATE_USERNAME = "USERNAME"
        self.STATE_CONFIRM_REGISTER = "CONFIRM_REGISTER"
        self.STATE_PASSWORD = "PASSWORD"
        self.STATE_REG_FIRST = "REG_FIRST"
        self.STATE_REG_LAST = "REG_LAST"
        self.STATE_REG_AGE = "REG_AGE"
        self.STATE_REG_PASS = "REG_PASS"
        self.STATE_REG_PASS_CONFIRM = "REG_PASS_CONFIRM"
        self.STATE_CONSOLE = "CONSOLE"
        self.STATE_SELECT_TECH = "SELECT_TECH"
        self.STATE_CONFIRM_RESET = "CONFIRM_RESET"
        self.STATE_QUIZ = "QUIZ"
        self.STATE_EDITOR = "EDITOR"

        self.current_state = self.STATE_USERNAME
        self.editor_row = 0
        self.editor_col = 0
        self.editor_status_msg = ""
        self.input_text = ""
        self.cursor_pos = 0
        self.temp_user = {}
        self.user_data = None
        self.available_techs_to_pick = []
        self.active_quiz = None
        self.command_history = []
        self.history_index = None
        self.replay_task_id = None
        self.map_cursor_idx = 0
        self.map_task_idx = 0

        self.console_lines = [
            "WITAJ W MINIMALISTYCZNYM EMULATORZE KOK BASIC",
            "--------------------------------------------",
            "Podaj nazwę użytkownika (login):",
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
        """Zwraca wybrane zadanie do powtórki (z Mapy Technologii) lub pierwsze nieukończone zadanie."""
        if not self.user_data:
            return None
        unlocked = set(self.user_data.get("unlocked_techs", []))
        if self.replay_task_id:
            replay_task = next(
                (t for t in self.tasks if t["id"] == self.replay_task_id and t.get("tech_id") in unlocked),
                None,
            )
            if replay_task:
                return replay_task
            self.replay_task_id = None

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
        self.bubble_notification = {"title": title, "message": message, "timer": duration_frames}

    def _on_pause(self, duration_sec: float):
        """Odświeża ekran i zatrzymuje wykonanie na czas PAUSE (tylko gdy aktywne jest okno gry)."""
        try:
            surf = pygame.display.get_surface()
            if surf is not None:
                w, h = surf.get_size()
                self.draw(surf, w, h)
                pygame.display.flip()
                pygame.event.pump()
                pygame.time.delay(int(min(duration_sec, 3.0) * 1000))
        except Exception:
            pass

    def is_tech_unlocked(self, tech_id: str) -> bool:
        """Sprawdza czy dana technologia jest już odblokowana przez gracza."""
        if not self.user_data:
            return False
        return tech_id in self.user_data.get("unlocked_techs", [])

    def get_unlocked_commands_for_tab(self) -> list[str]:
        """Zwraca listę komend dostępnych na pasku TAB na podstawie odblokowanych technologii."""
        unlocked = set(self.user_data.get("unlocked_techs", [])) if self.user_data else set()
        cmds = ["HELP", "PRINT", "QUIZ", "HINT"]
        if "CLS_1" in unlocked:
            cmds.append("CLS")
        if "HISTORY_1" in unlocked:
            cmds.append("HISTORY")
        if "CLOCK_1" in unlocked:
            cmds.extend(["DATE", "TIME", "PAUSE"])
        if any(t in unlocked for t in ["VAR_STR", "VAR_INT", "VAR_FLOAT", "VAR_BOOL"]):
            cmds.append("LET")
        if "VARS_1" in unlocked:
            cmds.extend(["VARS", "CLEAR"])
        if "RND_1" in unlocked:
            cmds.append("RANDOMIZE")
        if "INPUT_1" in unlocked:
            cmds.append("INPUT")
        if "IF_1" in unlocked:
            cmds.append("IF")
        if "FOR_1" in unlocked:
            cmds.append("FOR")
        if "DIM_1" in unlocked:
            cmds.extend(["DIM", "WHILE", "WEND", "GOTO", "REM", "END"])
        if "GFX_1" in unlocked:
            cmds.extend(["PIXEL", "LINE", "CIRCLE", "RECT", "TEXT"])
        if "COLOR_1" in unlocked:
            cmds.extend(["COLOR", "RGB"])
        if "MODE_1" in unlocked:
            cmds.extend(["MODE", "SCREEN"])
        if "GPIO_1" in unlocked:
            cmds.extend(["OUT", "IN"])
        if "SOUND_1" in unlocked:
            cmds.extend(["BEEP", "SOUND", "PLAY"])
        if "EDIT_1" in unlocked:
            cmds.extend(["NEW", "EDIT", "LIST", "SAVE", "LOAD", "FILES", "RUN", "CHECK"])
        if "EXIT_1" in unlocked:
            cmds.append("EXIT")
        return cmds

    def _refresh_available_techs(self):
        if not self.user_data:
            self.available_techs_to_pick = []
            return
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

    def get_tech_map_items(self) -> list[dict]:
        """Zwraca listę rozdziałów do widoku Mapy Technologii (odblokowane + dostępne do zakupu)."""
        return TechMapView.get_tech_map_items(self)

    def open_tech_map(self):
        """Otwiera interaktywną Mapę Technologii (powrót strzałkami do zadań lub zakup nowego poziomu)."""
        items = self.get_tech_map_items()
        self.map_cursor_idx = max(0, len(items) - 1)
        self.map_task_idx = 0
        self.current_state = self.STATE_SELECT_TECH

    def check_tech_completion(self):
        """Sprawdza, czy gracz ukończył wszystkie zadania ORAZ quizy dla aktywnej technologii i może kupić kolejną."""
        self._refresh_available_techs()

        if (
            self.available_techs_to_pick
            and self.current_state == self.STATE_CONSOLE
            and self.get_current_active_task() is None
            and len(self.get_available_quizzes()) == 0
        ):
            play_retro_victory_sound()
            self.console_lines.append("")
            self.console_lines.append("🎉 HURA! NOWY POZIOM DOSTĘPNY! (+1 🎓 Podpowiedź Profesora) 🎉")
            self.console_lines.append("Wybierz technologię (strzałki ↑/↓ lub wpisz numer 1-9 i wciśnij ENTER):")
            for idx, tech in enumerate(self.available_techs_to_pick, 1):
                self.console_lines.append(f"  [{idx}] {tech['name']} (Koszt: {tech['cost']} SP)")
            self.console_lines.append("")
            items = self.get_tech_map_items()
            self.map_cursor_idx = max(0, len(items) - 1)
            self.map_task_idx = 0
            self.current_state = self.STATE_SELECT_TECH

    def _complete_active_task_if_valid(self, command_str: str) -> bool:
        if not self.user_data:
            return False
        current_task = self.get_current_active_task()
        if current_task and QuestValidator.validate(current_task, command_str, self.user_data):
            task_id = current_task["id"]
            reward = current_task.get("reward_sp", 1)
            self.user_data["science_points"] = self.user_data.get("science_points", 0) + reward
            self.user_data.setdefault("completed_tasks", []).append(task_id)

            _, tech_sp_earned, tech_total_sp = self.get_active_tech_info()
            self.manager.save_user_state(self.user_data)
            self.disk_led_timer = 15
            play_retro_victory_sound()
            self.show_bubble_notification(
                f"🌟 BRAWO! (+{reward} SP)", f"Zadanie zaliczone!\nSP: {tech_sp_earned} / {tech_total_sp}"
            )
            return True
        return False

    def handle_keydown(self, event) -> bool:
        if event.key in [pygame.K_F1]:
            self.bubble_visible = not self.bubble_visible
            return True

        if event.key == pygame.K_F2 and self.user_data:
            if self.current_state == self.STATE_CONSOLE:
                self.open_tech_map()
                return True
            elif self.current_state == self.STATE_SELECT_TECH:
                self.current_state = self.STATE_CONSOLE
                return True

        # Nawigacja strzałkami oraz ESC w Mapie Technologii (STATE_SELECT_TECH)
        if self.current_state == self.STATE_SELECT_TECH and self.user_data:
            if TechMapView.handle_navigation_keydown(self, event):
                return True

        # --- OBSŁUGA PEŁNOEKRANOWEGO EDYTORA KODU (STATE_EDITOR) ---
        if self.current_state == self.STATE_EDITOR:
            return ProgramEditorView.handle_keydown(self, event)

        if event.key == pygame.K_LEFT:
            self.tab_active = False
            if self.cursor_pos > 0:
                self.cursor_pos -= 1
        elif event.key == pygame.K_RIGHT:
            self.tab_active = False
            if self.cursor_pos < len(self.input_text):
                self.cursor_pos += 1
        elif event.key == pygame.K_UP:
            self.tab_active = False
            if self.current_state == self.STATE_CONSOLE:
                if not self.is_tech_unlocked("HISTORY_1"):
                    self.console_lines.append("🔒 Historia komend (strzałki ↑/↓) nie jest jeszcze odblokowana!")
                    return True
                history = self.command_registry.history
                if history:
                    if self.history_index is None:
                        self.history_index = len(history) - 1
                    elif self.history_index > 0:
                        self.history_index -= 1
                    self.input_text = history[self.history_index]
                    self.cursor_pos = len(self.input_text)
                    if self.user_data:
                        self.user_data.setdefault("action_counts", {})
                        self.user_data["action_counts"]["UP"] = self.user_data["action_counts"].get("UP", 0) + 1
                        if self._complete_active_task_if_valid("UP"):
                            self.check_tech_completion()
        elif event.key == pygame.K_DOWN:
            self.tab_active = False
            if self.current_state == self.STATE_CONSOLE:
                if not self.is_tech_unlocked("HISTORY_1"):
                    self.console_lines.append("🔒 Historia komend (strzałki ↑/↓) nie jest jeszcze odblokowana!")
                    return True
                history = self.command_registry.history
                if history and self.history_index is not None:
                    if self.history_index < len(history) - 1:
                        self.history_index += 1
                        self.input_text = history[self.history_index]
                    else:
                        self.history_index = None
                        self.input_text = ""
                    self.cursor_pos = len(self.input_text)
        elif event.key == pygame.K_BACKSPACE:
            self.tab_active = False
            if self.cursor_pos > 0:
                self.input_text = self.input_text[: self.cursor_pos - 1] + self.input_text[self.cursor_pos :]
                self.cursor_pos -= 1
        elif event.key == pygame.K_DELETE:
            self.tab_active = False
            if self.cursor_pos < len(self.input_text):
                self.input_text = self.input_text[: self.cursor_pos] + self.input_text[self.cursor_pos + 1 :]
        elif event.key == pygame.K_TAB:
            if self.current_state == self.STATE_CONSOLE and self.user_data:
                if not self.is_tech_unlocked("TAB_1"):
                    self.console_lines.append("🔒 Skrót TAB nie jest jeszcze odblokowany!")
                    return True

                unlocked_cmds = self.get_unlocked_commands_for_tab()

                if self.tab_active and self.tab_suggestions:
                    self.tab_selected_index = (self.tab_selected_index + 1) % len(self.tab_suggestions)
                else:
                    raw_prefix = self.input_text.strip().upper()
                    matches = [c for c in unlocked_cmds if c.startswith(raw_prefix)] if raw_prefix else unlocked_cmds
                    if not matches:
                        matches = unlocked_cmds
                    self.tab_suggestions = matches
                    self.tab_selected_index = 0
                    self.tab_active = True

                chosen_cmd = self.tab_suggestions[self.tab_selected_index]
                self.input_text = chosen_cmd + " "
                self.cursor_pos = len(self.input_text)

                if "action_counts" not in self.user_data:
                    self.user_data["action_counts"] = {}
                self.user_data["action_counts"]["TAB"] = self.user_data["action_counts"].get("TAB", 0) + 1

                if self._complete_active_task_if_valid("TAB"):
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
                    self.console_lines.append(f"Nie znaleziono użytkownika '{line}'. Czy chcesz utworzyć nowe konto? (T/N):")
                    self.current_state = self.STATE_CONFIRM_REGISTER

            elif self.current_state == self.STATE_CONFIRM_REGISTER:
                self.console_lines.append(f"> {line}")
                ans = line.strip().upper()
                if ans in ("T", "TAK", "Y", "YES"):
                    self.console_lines.append("Rozpoczynamy rejestrację. Podaj swoje imię:")
                    self.current_state = self.STATE_REG_FIRST
                elif ans in ("N", "NIE", "NO"):
                    self.console_lines.append("Powrót do logowania.")
                    self.console_lines.append("Podaj nazwę użytkownika (login):")
                    self.temp_user = {}
                    self.current_state = self.STATE_USERNAME
                else:
                    self.console_lines.append("Wpisz T (Tak, aby utworzyć konto) lub N (Nie, aby wrócić do logowania):")

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
                                "🎉 BRAWO! (+5 SP)", "Wróciłeś do KOK BASIC!\nZadanie EXIT zaliczone!"
                            )

                    self.console_lines.append(f"Zalogowano pomyślnie! Witaj, {self.user_data['first_name']}.")
                    unlocked = self.user_data.get("unlocked_techs", [])
                    self.console_lines.append(f"Odblokowane technologie: {', '.join(unlocked) if unlocked else 'Brak'}")
                    _, tech_sp_earned, tech_total_sp = self.get_active_tech_info()
                    self.console_lines.append(f"Punkty SP: {tech_sp_earned} / {tech_total_sp}")
                    self.command_registry.program_lines = list(self.user_data.get("program_lines", [""])) or [""]
                    self.command_registry.saved_programs = dict(self.user_data.get("saved_programs", {}))
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
                if not line:
                    self.console_lines.append("Hasło nie może być puste! Podaj hasło:")
                    return True
                self.console_lines.append("> ****")
                self.temp_user["password_candidate"] = line
                self.console_lines.append("Powtórz hasło:")
                self.current_state = self.STATE_REG_PASS_CONFIRM

            elif self.current_state == self.STATE_REG_PASS_CONFIRM:
                self.console_lines.append("> ****")
                if line != self.temp_user.get("password_candidate"):
                    self.console_lines.append("❌ Hasła nie są takie same! Spróbuj ponownie.")
                    self.temp_user["password_candidate"] = None
                    self.console_lines.append("Utwórz hasło do konta:")
                    self.current_state = self.STATE_REG_PASS
                    return True

                self.user_data = self.manager.register_user(
                    username=self.temp_user["username"],
                    first_name=self.temp_user["first_name"],
                    last_name=self.temp_user["last_name"],
                    age=self.temp_user["age"],
                    password=line,
                )
                self.disk_led_timer = 15
                self.console_lines.append("Konto utworzone pomyślnie!")
                _, tech_sp_earned, tech_total_sp = self.get_active_tech_info()
                self.console_lines.append(f"Punkty SP: {tech_sp_earned} / {tech_total_sp}")
                self.current_state = self.STATE_CONSOLE
                self.check_tech_completion()

            elif self.current_state == self.STATE_SELECT_TECH:
                TechMapView.handle_selection_return(self, line)

            elif self.current_state == self.STATE_QUIZ:
                self.console_lines.append(f"> {line}")
                if not self.active_quiz:
                    self.current_state = self.STATE_CONSOLE
                    return True

                if line in ["1", "2", "3", "4"]:
                    chosen_ans = int(line)
                    if chosen_ans == self.active_quiz.get("correct"):
                        qid = self.active_quiz["id"]
                        self.user_data.setdefault("completed_quizzes", []).append(qid)
                        self.user_data["science_points"] = self.user_data.get("science_points", 0) + 1
                        self.manager.save_user_state(self.user_data)
                        self.disk_led_timer = 15
                        play_retro_victory_sound()

                        rem = len(self.get_available_quizzes())
                        self.console_lines.append("✅ DOBRA ODPOWIEDŹ! Zdobywasz +1 SP!")
                        if rem > 0:
                            self.console_lines.append(f"Pozostało pytań quizowych: {rem}. Wpisz QUIZ, aby kontynuować!")
                        self.show_bubble_notification(
                            "🌟 QUIZ ZALICZONY! (+1 SP)",
                            f"Świetna odpowiedź!\nPozostało quizów: {rem}",
                        )
                        self.active_quiz = None
                        self.current_state = self.STATE_CONSOLE
                        self.check_tech_completion()
                    else:
                        play_retro_fail_sound()
                        self.console_lines.append("❌ Niestety, to błędna odpowiedź! Spróbuj jeszcze raz (wpisz QUIZ).")
                        self.show_bubble_notification(
                            "❌ BŁĘDNA ODPOWIEDŹ",
                            "Nie martw się! Wpisz ponownie QUIZ i spróbuj jeszcze raz.",
                        )
                        self.active_quiz = None
                        self.current_state = self.STATE_CONSOLE
                else:
                    self.console_lines.append("Wpisz numer odpowiedzi od 1 do 4!")

            elif self.current_state == self.STATE_CONFIRM_RESET:
                self.console_lines.append(f"> {line}")
                if line.upper() in ["T", "TAK", "Y", "YES"]:
                    username = self.user_data["username"]
                    self.manager.delete_user(username)
                    self.user_data = None
                    self.temp_user = {}
                    self.console_lines = [
                        "Profil został całkowicie usunięty.",
                        "--------------------------------------------",
                        "Podaj nazwę użytkownika (login):",
                    ]
                    self.current_state = self.STATE_USERNAME
                else:
                    self.console_lines.append("Anulowano resetowanie profilu.")
                    self.current_state = self.STATE_CONSOLE

            # --- WYKONYWANIE KOMEND W KONSOLI ---
            elif self.current_state == self.STATE_CONSOLE:
                if not line:
                    return True
                self.console_lines.append(f"> {line}")
                self.history_index = None

                if line.upper() == "QUIZ":
                    avail_q = self.get_available_quizzes()
                    if not avail_q:
                        self.console_lines.append("Wszystkie dostępne quizy z obecnych technologii zostały już rozwiązane!")
                    else:
                        self.active_quiz = avail_q[0]
                        self.current_state = self.STATE_QUIZ
                        self.console_lines.append(f"=== PYTANIE QUIZOWE ({len(avail_q)} pozostało) ===")
                        self.console_lines.append(self.active_quiz["question"])
                        for i, opt in enumerate(self.active_quiz["options"], 1):
                            self.console_lines.append(f"  [{i}] {opt}")
                        self.console_lines.append("Wpisz numer odpowiedzi (1-4) i naciśnij ENTER:")
                    return True

                if line.upper() == "EXIT":
                    current_task = self.get_current_active_task()
                    if current_task and current_task["id"] == "exit_task":
                        self.user_data["exit_task_pending"] = True
                    self.manager.save_user_state(self.user_data)
                    return False

                if line.upper() in ("MAPA", "TECH"):
                    self.open_tech_map()
                    return True

                if line.upper() == "DALEJ":
                    self.replay_task_id = None
                    self.console_lines.append("▶️ Powrót do kolejnego nieukończonego zadania.")
                    return True

                if line.upper() == "_RESET":
                    self.console_lines.append("⚠️ UWAGA: Czy na pewno chcesz usunąć profil? (T/N)")
                    self.current_state = self.STATE_CONFIRM_RESET
                    return True

                first_tok = line.split()[0].upper()

                if first_tok == "HISTORY" and not self.is_tech_unlocked("HISTORY_1"):
                    self.console_lines.append("🔒 Komenda HISTORY nie jest jeszcze odblokowana!")
                    return True

                if first_tok in ("DATE", "TIME") and not self.is_tech_unlocked("CLOCK_1"):
                    self.console_lines.append(f"🔒 Komenda {first_tok} nie jest jeszcze odblokowana!")
                    return True

                if first_tok in ("PAUSE", "WAIT", "SLEEP") and not (
                    self.is_tech_unlocked("CLOCK_1") or self.is_tech_unlocked("EDIT_1")
                ):
                    self.console_lines.append(f"🔒 Komenda {first_tok} nie jest jeszcze odblokowana!")
                    return True

                if first_tok in ("VARS", "CLEAR") and not self.is_tech_unlocked("VARS_1"):
                    self.console_lines.append(f"🔒 Komenda {first_tok} nie jest jeszcze odblokowana!")
                    return True

                if first_tok == "IF" and not self.is_tech_unlocked("IF_1"):
                    self.console_lines.append("🔒 Komenda IF nie jest jeszcze odblokowana!")
                    return True

                if first_tok == "FOR" and not self.is_tech_unlocked("FOR_1"):
                    self.console_lines.append("🔒 Komenda FOR nie jest jeszcze odblokowana!")
                    return True

                if first_tok == "RANDOMIZE" and not (
                    self.is_tech_unlocked("RND_1") or self.is_tech_unlocked("EDIT_1")
                ):
                    self.console_lines.append("🔒 Komenda RANDOMIZE nie jest jeszcze odblokowana!")
                    return True

                if first_tok == "INPUT" and not (
                    self.is_tech_unlocked("INPUT_1") or self.is_tech_unlocked("EDIT_1")
                ):
                    self.console_lines.append("🔒 Komenda INPUT nie jest jeszcze odblokowana!")
                    return True

                if first_tok in ("DIM", "WHILE", "WEND", "GOTO") and not (
                    self.is_tech_unlocked("DIM_1") or self.is_tech_unlocked("EDIT_1")
                ):
                    self.console_lines.append(f"🔒 Komenda {first_tok} nie jest jeszcze odblokowana!")
                    return True

                if first_tok in ("PIXEL", "PSET", "LINE", "CIRCLE", "RECT", "BOX", "TEXT", "DRAWTEXT") and not self.is_tech_unlocked("GFX_1"):
                    self.console_lines.append(f"🔒 Komenda {first_tok} nie jest jeszcze odblokowana!")
                    return True

                if first_tok in ("COLOR", "RGB", "KOLOR") and not (
                    self.is_tech_unlocked("COLOR_1") or self.is_tech_unlocked("EDIT_1")
                ):
                    self.console_lines.append(f"🔒 Komenda {first_tok} nie jest jeszcze odblokowana!")
                    return True

                if first_tok in ("MODE", "SCREEN") and not (
                    self.is_tech_unlocked("MODE_1") or self.is_tech_unlocked("EDIT_1")
                ):
                    self.console_lines.append(f"🔒 Komenda {first_tok} nie jest jeszcze odblokowana! Odblokuj technologię MODE_1!")
                    return True

                if first_tok in ("OUT", "LED", "GPIO", "IN") and not self.is_tech_unlocked("GPIO_1"):
                    self.console_lines.append(f"🔒 Komenda {first_tok} nie jest jeszcze odblokowana!")
                    return True

                if first_tok in ("BEEP", "SOUND", "TONE", "PLAY") and not self.is_tech_unlocked("SOUND_1"):
                    self.console_lines.append(f"🔒 Komenda {first_tok} nie jest jeszcze odblokowana!")
                    return True

                if first_tok in ("NEW", "EDIT", "LIST", "SAVE", "LOAD", "FILES", "DIR", "RUN", "CHECK", "OCEN") and not self.is_tech_unlocked("EDIT_1"):
                    self.console_lines.append(f"🔒 Komenda {first_tok} nie jest jeszcze odblokowana!")
                    return True

                variables = self.user_data.setdefault("variables", {}) if self.user_data else None
                self.command_registry.active_user_data = self.user_data
                self.command_registry.active_task = self.get_current_active_task()
                self.command_registry.last_check_result = None
                self.command_registry.last_hint_result = None
                found, success = self.command_registry.execute_command(line, self.console_lines, variables)

                if not found:
                    self.console_lines.append(f"SYNTAX ERROR: Nieznana komenda '{first_tok}'")
                    return True

                if success:
                    if self.user_data is not None:
                        self.user_data["program_lines"] = list(self.command_registry.program_lines)
                        self.user_data["saved_programs"] = dict(self.command_registry.saved_programs)
                        if first_tok in ("SAVE", "NEW", "LOAD"):
                            self.disk_led_timer = 15
                            self.manager.save_user_state(self.user_data)

                    if getattr(self.command_registry, "last_hint_result", None):
                        hint_res = self.command_registry.last_hint_result
                        self.show_bubble_notification(
                            "🎓 PODPOWIEDŹ PROFESORA KOK-88",
                            hint_res.get("message", ""),
                            duration_frames=1800,
                        )
                        if self.user_data is not None:
                            self.manager.save_user_state(self.user_data)

                    if getattr(self.command_registry, "last_check_result", None):
                        chk_res = self.command_registry.last_check_result
                        if chk_res.get("rate_limited"):
                            self.show_bubble_notification(
                                "☕ PRZERWA NA HERBATKĘ!",
                                chk_res.get("message", ""),
                                duration_frames=600,
                            )
                        else:
                            sc = chk_res.get("total_score", 0)
                            cur_t = self.get_current_active_task()
                            if cur_t and self.user_data is not None:
                                tid = cur_t["id"]
                                scores = self.user_data.setdefault("task_scores", {})
                                prev_best = scores.get(tid, 0)
                                if sc > prev_best:
                                    diff_sp = sc - prev_best
                                    scores[tid] = sc
                                    self.user_data["science_points"] = self.user_data.get("science_points", 0) + diff_sp
                                    self.console_lines.append(
                                        f"🌟 NOWY REKORD OCENY ZADANIA: {sc}/10 pkt! (+{diff_sp} SP)"
                                    )
                            self.show_bubble_notification(
                                f"🎓 OCENA PROFESORA: {sc}/10 PKT",
                                f"Błędy/Wynik: {chk_res['error_free_and_correct_pts']}/4 | Czas: {chk_res['time_pts']}/2 | Kod: {chk_res['quality_pts']}/4\n\n{chk_res.get('feedback', '')}",
                                duration_frames=1800,
                            )
                        if self.user_data is not None:
                            self.manager.save_user_state(self.user_data)

                    if getattr(self.command_registry, "open_editor_requested", False):
                        self.command_registry.open_editor_requested = False
                        self.current_state = self.STATE_EDITOR
                        plines = self.command_registry.program_lines
                        self.editor_row = max(0, len(plines) - 1)
                        self.editor_col = len(plines[self.editor_row])
                        self.editor_status_msg = "Wpisz kod programu. [Ctrl+S] Zapisz | [ESC] Zamknij edytor"

                    cmd_name = first_tok
                    if "=" in cmd_name and not cmd_name.startswith("LET"):
                        cmd_name = cmd_name.split("=")[0].strip()
                    if "action_counts" not in self.user_data:
                        self.user_data["action_counts"] = {}
                    self.user_data["action_counts"][cmd_name] = self.user_data["action_counts"].get(cmd_name, 0) + 1

                    task_completed_now = False
                    current_task = self.get_current_active_task()

                    if current_task and QuestValidator.validate(current_task, line, self.user_data):
                        task_id = current_task["id"]
                        completed_list = self.user_data.setdefault("completed_tasks", [])
                        if task_id not in completed_list:
                            reward = current_task.get("reward_sp", 1)
                            self.user_data["science_points"] = self.user_data.get("science_points", 0) + reward
                            completed_list.append(task_id)

                            _, tech_sp_earned, tech_total_sp = self.get_active_tech_info()
                            self.manager.save_user_state(self.user_data)
                            self.disk_led_timer = 15
                            play_retro_victory_sound()
                            if not getattr(self.command_registry, "last_check_result", None):
                                self.show_bubble_notification(
                                    f"🌟 BRAWO! (+{reward} SP)",
                                    f"Zadanie zaliczone!\nSP: {tech_sp_earned} / {tech_total_sp}",
                                )
                            task_completed_now = True
                        if self.replay_task_id == task_id:
                            chk_sc = self.user_data.get("task_scores", {}).get(task_id, 0)
                            if cmd_name not in ("CHECK", "OCEN") or chk_sc >= 10:
                                self.replay_task_id = None
                    elif (
                        current_task
                        and cmd_name == "RUN"
                        and current_task.get("validation", {}).get("type") == "program_run"
                    ):
                        _, hint_msg = QuestValidator.validate_program_run_with_feedback(current_task, self.user_data)
                        if hint_msg:
                            self.console_lines.append(hint_msg)
                            self.show_bubble_notification("🤖 PROFESOR KOK-88 PODPOWIADA", hint_msg, duration_frames=240)

                    if task_completed_now:
                        self.check_tech_completion()
        else:
            if hasattr(event, "unicode") and event.unicode and event.unicode.isprintable():
                self.tab_active = False
                self.input_text = self.input_text[: self.cursor_pos] + event.unicode + self.input_text[self.cursor_pos :]
                self.cursor_pos += 1
        return True

    def _build_chassis_surface(self, width, height, margin_x, margin_top, screen_w, screen_h, panel_height, corner_radius):
        return CRTChassisRenderer.build_chassis_surface(
            width, height, margin_x, margin_top, screen_w, screen_h, panel_height, self.model_font, self.gpio_num_font
        )

    def draw(self, screen, width, height):
        margin_x = 48
        margin_top = 40
        panel_height = 68
        screen_w = width - (margin_x * 2)
        screen_h = height - margin_top - panel_height - 24

        crt_rect = pygame.Rect(margin_x, margin_top, screen_w, screen_h)
        corner_radius = 18

        if self._crt_cache_size != (screen_w, screen_h):
            self._crt_cache_size = (screen_w, screen_h)
            self._crt_surf = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)

            self._scanline_surf = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
            for y in range(0, screen_h, 3):
                pygame.draw.line(self._scanline_surf, (0, 0, 0, 60), (0, y), (screen_w, y), 1)

            self._glass_overlay_surf = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
            for inset, alpha in [(0, 95), (3, 60), (7, 30), (12, 15)]:
                pygame.draw.rect(
                    self._glass_overlay_surf,
                    (0, 0, 0, alpha),
                    (inset, inset, screen_w - inset * 2, screen_h - inset * 2),
                    width=4,
                    border_radius=max(4, corner_radius - inset),
                )
            glare_poly = [
                (25, 14),
                (min(260, screen_w // 2), 14),
                (min(180, screen_w // 3), 55),
                (25, 95),
            ]
            pygame.draw.polygon(self._glass_overlay_surf, (255, 255, 255, 12), glare_poly)

            self._mask_surf = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
            self._mask_surf.fill((0, 0, 0, 0))
            pygame.draw.rect(self._mask_surf, (255, 255, 255, 255), (0, 0, screen_w, screen_h), border_radius=corner_radius)

            self._chassis_surf = self._build_chassis_surface(
                width, height, margin_x, margin_top, screen_w, screen_h, panel_height, corner_radius
            )

        screen.blit(self._chassis_surf, (0, 0))

        crt_surf = self._crt_surf
        crt_surf.fill((10, 20, 10))

        hud_height = 30
        pygame.draw.rect(crt_surf, (15, 30, 15), (0, 0, screen_w, hud_height))
        pygame.draw.line(crt_surf, (40, 80, 40), (0, hud_height), (screen_w, hud_height), 1)

        if self.user_data and self.current_state in [
            self.STATE_CONSOLE,
            self.STATE_QUIZ,
            self.STATE_EDITOR,
            self.STATE_SELECT_TECH,
        ]:
            active_task = self.get_current_active_task()
            avail_quizzes = self.get_available_quizzes()
            if self.current_state == self.STATE_SELECT_TECH:
                mission_text = "🗺️ MAPA TECHNOLOGII (↑/↓ rozdział, ←/→ zadanie, ENTER wybierz)"
            elif active_task:
                prefix = "🔄 POWTÓRKA: " if self.replay_task_id else "🎯 MISJA: "
                mission_text = f"{prefix}{active_task['title']}"
            elif avail_quizzes:
                mission_text = f"🧠 QUIZ: Wpisz QUIZ (pozostało: {len(avail_quizzes)})"
            else:
                mission_text = "🎉 POZIOM UKOŃCZONY! ([F2] Mapa)"
            _, tech_sp_earned, tech_total_sp = self.get_active_tech_info()
            total_sp = self.user_data.get("science_points", 0)
            hints_cnt = self.user_data.get("professor_hints", 1)
            clock_part = f" | ☼ {datetime.now().strftime('%H:%M:%S')}" if self.is_tech_unlocked("CLOCK_1") else ""
            sp_text = f"♦ SP: {total_sp} ({tech_sp_earned}/{tech_total_sp}) | ☼ HINT: {hints_cnt} | [F2] Mapa{clock_part} | {self.user_data.get('first_name', '')}"

            mission_surf = self.hud_font.render(mission_text, True, (0, 255, 120))
            sp_surf = self.hud_font.render(sp_text, True, (0, 220, 255))

            crt_surf.blit(mission_surf, (15, 6))
            crt_surf.blit(sp_surf, (max(screen_w - sp_surf.get_width() - 15, 250), 6))
        else:
            logo_surf = self.hud_font.render("KOK BASIC - Retro Emulator Edukacyjny", True, (0, 200, 100))
            crt_surf.blit(logo_surf, (15, 6))

        if self.current_state == self.STATE_EDITOR:
            ProgramEditorView.draw(self, crt_surf, screen_w, screen_h, hud_height)
        elif self.current_state == self.STATE_SELECT_TECH and self.user_data:
            TechMapView.draw(self, crt_surf, screen_w, screen_h, hud_height)
        else:
            line_height = 24
            max_lines = max(1, (screen_h - hud_height - 60) // line_height)
            max_line_w = max(240, screen_w - 40)

            wrapped_entries = []
            for raw_line in self.console_lines[-max_lines:]:
                if "HURA" in raw_line or "⭐" in raw_line:
                    color = (255, 100, 200)
                elif raw_line.startswith("⚠️") or "SYNTAX ERROR" in raw_line or raw_line.startswith("❌"):
                    color = (255, 80, 80)
                elif "PROFESOR" in raw_line or raw_line.strip().startswith("💬") or raw_line.startswith("🎓"):
                    color = (255, 225, 100)
                elif "✅" in raw_line or "Zalogowano" in raw_line or "BRAWO" in raw_line:
                    color = (80, 255, 80)
                else:
                    color = (150, 255, 150)

                for wline in wrap_text(raw_line, self.font, max_line_w):
                    wrapped_entries.append((wline, color))

            visible_entries = wrapped_entries[-max_lines:]
            num_lines = len(visible_entries)
            bottom_limit = screen_h - 45
            start_y = bottom_limit - (num_lines * line_height)
            y_offset = max(hud_height + 10, start_y)

            for wline, color in visible_entries:
                text_surface = self.font.render(wline, True, color)
                crt_surf.blit(text_surface, (20, y_offset))
                y_offset += line_height

            CRTChassisRenderer.draw_vga_layer(self, crt_surf, screen_w, screen_h, hud_height)

        # --- DYMEK MISJI (F1) ---
        if self.user_data and self.current_state in [self.STATE_CONSOLE, self.STATE_QUIZ, self.STATE_EDITOR]:
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

                active_task = self.get_current_active_task()
                avail_quizzes = self.get_available_quizzes()

                task_title = ""
                task_color = (255, 220, 50)
                task_body = ""

                if self.current_state == self.STATE_QUIZ and self.active_quiz:
                    task_title = "🧠 PYTANIE QUIZOWE (+1 SP)"
                    task_color = (80, 230, 255)
                    opts = "\n".join(f"[{i}] {o}" for i, o in enumerate(self.active_quiz["options"], 1))
                    task_body = f"{self.active_quiz['question']}\n\n{opts}\n\nWpisz numer 1-4 i wciśnij ENTER!"
                elif active_task:
                    prefix = "🔄 POWTÓRKA: " if self.replay_task_id else "💬 "
                    task_title = f"{prefix}{active_task['title']}"
                    task_color = (255, 220, 50)
                    task_body = active_task.get("instruction", "")
                elif avail_quizzes:
                    task_title = f"🧠 CZAS NA QUIZ! (Pozostało: {len(avail_quizzes)})"
                    task_color = (80, 230, 255)
                    task_body = (
                        f"Brawo! Wykonałeś wszystkie ćwiczenia z tego poziomu!\n\n"
                        f"Aby przejść dalej, rozwiąż jeszcze {len(avail_quizzes)} "
                        f"pytania quizowe (+1 SP za każde).\n"
                        f"Wpisz komendę QUIZ i wciśnij ENTER!"
                    )
                else:
                    task_title = "🎉 POZIOM UKOŃCZONY!"
                    task_color = (255, 100, 200)
                    task_body = "Wszystkie zadania i quizy ukończone."

                # Podpowiedź / notyfikacja od Profesora KOK-88
                hint_title = ""
                hint_body = ""
                if self.bubble_notification and self.bubble_notification.get("timer", 0) > 0:
                    self.bubble_notification["timer"] -= 1
                    hint_title = self.bubble_notification.get("title", "🤖 PODPOWIEDŹ PROFESORA KOK-88:")
                    hint_body = self.bubble_notification.get("message", "")

                task_title_lines = wrap_text(task_title, self.bubble_title_font, bubble_width - 28)
                task_body_lines = []
                for paragraph in task_body.split("\n"):
                    task_body_lines.extend(wrap_text(paragraph, self.bubble_font, bubble_width - 28))

                has_hint = bool(hint_body)
                hint_title_lines = wrap_text(hint_title, self.bubble_title_font, bubble_width - 28) if has_hint else []
                hint_body_lines = []
                if has_hint:
                    for paragraph in hint_body.split("\n"):
                        hint_body_lines.extend(wrap_text(paragraph, self.bubble_font, bubble_width - 28))

                title_line_h = 24
                line_h = 22
                content_h = 14 + (len(task_title_lines) * title_line_h) + 6 + (len(task_body_lines) * line_h) + 28
                if has_hint:
                    content_h += 8 + (len(hint_title_lines) * title_line_h) + 4 + (len(hint_body_lines) * line_h) + 6

                bubble_surf = pygame.Surface((bubble_width, content_h), pygame.SRCALPHA)
                bg_border_color = (80, 240, 220) if has_hint else (80, 220, 110)
                pygame.draw.rect(bubble_surf, (10, 28, 16, 245), (0, 0, bubble_width, content_h), border_radius=8)
                pygame.draw.rect(bubble_surf, bg_border_color, (0, 0, bubble_width, content_h), width=2, border_radius=8)

                # 1. Rysowanie tytułu zadania
                ty = 12
                for tl in task_title_lines:
                    t_surf = self.bubble_title_font.render(tl, True, task_color)
                    bubble_surf.blit(t_surf, (14, ty))
                    ty += title_line_h

                # 2. Linia podziału zadania
                div_y = ty + 2
                pygame.draw.line(bubble_surf, (50, 130, 75), (14, div_y), (bubble_width - 14, div_y), 1)

                # 3. Treść zadania
                curr_y = div_y + 6
                for bl in task_body_lines:
                    b_surf = self.bubble_font.render(bl, True, (215, 255, 215))
                    bubble_surf.blit(b_surf, (14, curr_y))
                    curr_y += line_h

                # 4. Sekcja podpowiedzi profesora (jeśli aktywna)
                if has_hint:
                    curr_y += 4
                    pygame.draw.line(bubble_surf, (30, 150, 180), (14, curr_y), (bubble_width - 14, curr_y), 1)
                    curr_y += 8
                    for htl in hint_title_lines:
                        ht_surf = self.bubble_title_font.render(htl, True, (80, 240, 255))
                        bubble_surf.blit(ht_surf, (14, curr_y))
                        curr_y += title_line_h
                    curr_y += 2
                    for hbl in hint_body_lines:
                        hb_surf = self.bubble_font.render(hbl, True, (255, 240, 150))
                        bubble_surf.blit(hb_surf, (14, curr_y))
                        curr_y += line_h

                # 5. Etykietka [F1] Schowaj
                hint_surf = self.bubble_font.render("[F1] Schowaj", True, (110, 165, 125))
                bubble_surf.blit(hint_surf, (bubble_width - hint_surf.get_width() - 14, content_h - 26))

                crt_surf.blit(bubble_surf, (bubble_x, bubble_y))

        # --- PASEK PODPOWIEDZI TAB (STYL IPHONE) ---
        if self.tab_active and self.tab_suggestions and self.current_state == self.STATE_CONSOLE:
            bar_y = screen_h - 68
            bar_x = 20
            hint_lbl = self.bubble_font.render("TAB ▸", True, (90, 180, 110))
            crt_surf.blit(hint_lbl, (bar_x, bar_y + 4))
            bar_x += hint_lbl.get_width() + 10

            for idx, cmd_name in enumerate(self.tab_suggestions):
                is_sel = idx == self.tab_selected_index
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

        # --- LINIA INPUTU I KURSOR (GDY NIE JESTEŚMY W EDYTORZE) ---
        if self.current_state != self.STATE_EDITOR:
            prompt_symbol = "KOK-BASIC> " if self.current_state == self.STATE_CONSOLE else ">> "
            if self.current_state == self.STATE_CONFIRM_RESET:
                prompt_symbol = "RESET (T/N)> "
            elif self.current_state == self.STATE_SELECT_TECH:
                prompt_symbol = "WYBIERZ TECH> "
            elif self.current_state == self.STATE_QUIZ:
                prompt_symbol = "ODPOWIEDŹ (1-4)> "

            display_text = (
                "*" * len(self.input_text)
                if self.current_state in [self.STATE_PASSWORD, self.STATE_REG_PASS, self.STATE_REG_PASS_CONFIRM]
                else self.input_text
            )

            text_left = display_text[: self.cursor_pos]
            text_right = display_text[self.cursor_pos :]

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

        crt_surf.blit(self._scanline_surf, (0, 0))
        crt_surf.blit(self._glass_overlay_surf, (0, 0))
        crt_surf.blit(self._mask_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)

        screen.blit(crt_surf, (margin_x, margin_top))

        pygame.draw.rect(screen, (38, 42, 38), crt_rect.inflate(4, 4), width=5, border_radius=corner_radius + 2)
        pygame.draw.rect(screen, (14, 16, 14), crt_rect, width=4, border_radius=corner_radius)
        pygame.draw.rect(screen, (30, 75, 40), crt_rect.inflate(-2, -2), width=1, border_radius=corner_radius)

        CRTChassisRenderer.draw_led_panel(self, screen, margin_x, margin_top, screen_h)
