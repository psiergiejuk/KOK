import re

def normalize_code(s: str) -> str:
    """Normalizuje komendę: wielkie litery, redukcja spacji, usunięcie spacji wokół operatorów."""
    s = re.sub(r'\s+', ' ', s.strip().upper())
    s = re.sub(r'\s*([=+\-*/(),;])\s*', r'\1', s)
    return s

class QuestValidator:
    @staticmethod
    def validate_program_run_with_feedback(task: dict, user_data: dict) -> tuple[bool, str | None]:
        """
        Weryfikuje wielolinijkowy program napisany w EDIT i uruchomiony komendą RUN.
        Zwraca (czy_zaliczone, wskazówka_profesora_gdy_brakuje_elementu).
        """
        val_cfg = task.get("validation", {})
        if "program_lines" in user_data:
            raw_lines = user_data.get("program_lines") or []
        else:
            raw_lines = task.get("sample_program") or []

        requires_rem = any(kw.upper() in ("REM", "'") for kw in val_cfg.get("required_keywords", []))
        clean_lines = [
            re.sub(r'^\d+\s+', '', l).strip()
            for l in raw_lines
            if l and l.strip() and (requires_rem or not l.strip().upper().startswith("REM"))
        ]

        if not clean_lines:
            return False, (
                "🤖 PROFESOR KOK-88: Kartka w edytorze jest pusta jak brzuch przed śniadaniem! "
                "Wpisz EDIT, napisz program, wyjdź klawiszem ESC i wpisz RUN."
            )

        min_lines = val_cfg.get("min_lines", 1)
        if len(clean_lines) < min_lines:
            return False, (
                f"🤖 PROFESOR KOK-88: Twój program ma dopiero {len(clean_lines)} linijkę, "
                f"a w tym zadaniu potrzebujemy co najmniej {min_lines} linijek kodu w EDIT!"
            )

        upper_code = "\n".join(clean_lines).upper()

        expected_output = val_cfg.get("expected_output")
        if expected_output:
            expected_upper = expected_output.upper()
            if expected_upper not in upper_code and not any("PRINT" in l.upper() for l in raw_lines):
                return False, f"🤖 WSKAZÓWKA PROFESORA: Program powinien wyświetlić: {expected_output}!"

        for kw in val_cfg.get("required_keywords", []):
            if kw.upper() not in upper_code:
                custom_hint = val_cfg.get(
                    "hint",
                    f"W Twoim programie w EDIT brakuje jeszcze elementu: {kw.upper()}!"
                )
                return False, f"🤖 WSKAZÓWKA PROFESORA: {custom_hint}"

        for group in val_cfg.get("any_keywords", []):
            if not any(opt.upper() in upper_code for opt in group):
                opts_str = " lub ".join(group)
                custom_hint = val_cfg.get(
                    "hint",
                    f"Użyj w programie przynajmniej jednej z komend: {opts_str}!"
                )
                return False, f"🤖 WSKAZÓWKA PROFESORA: {custom_hint}"

        if val_cfg.get("require_quotes", False):
            if not re.search(r'"[^"]*"|\'[^\']*\'', upper_code):
                return False, "🤖 WSKAZÓWKA PROFESORA: Pamiętaj o cudzysłowie \"...\" wokół wypisywanego napisu!"

        return True, None

    @staticmethod
    def validate(task, command_line, user_data) -> bool:
        v_type = task["validation"]["type"]

        if v_type == "exit_restart":
            return command_line.strip().upper() == "EXIT"

        elif v_type == "program_run":
            cmd_word = command_line.strip().split()[0].upper() if command_line.strip() else ""
            if cmd_word not in ("RUN", "CHECK", "OCEN"):
                return False
            passed, _ = QuestValidator.validate_program_run_with_feedback(task, user_data)
            return passed
        
        elif v_type == "command_prefix":
            target = task["validation"]["target"].upper()
            require_quotes = task["validation"].get("require_quotes", False)
            
            clean_cmd = command_line.strip()
            if not clean_cmd:
                return False

            if " " in target:
                if not clean_cmd.upper().startswith(target):
                    return False
            else:
                parts = clean_cmd.split(maxsplit=1)
                cmd = parts[0].upper()
                if cmd == "CLR":
                    cmd = "CLS"
                
                # Obsługa przypisań bez spacji, np. A=5 gdy target to "A"
                if "=" in parts[0] and not parts[0].upper().startswith("LET"):
                    cmd = parts[0].split("=")[0].strip().upper()

                if cmd != target:
                    return False
                    
                # Komendy oczekujące argumentów (np. PRINT, HELP) nie mogą być puste
                no_arg_cmds = [
                    "CLS", "EXIT", "HISTORY", "TAB", "DATE", "TIME",
                    "VARS", "CLEAR", "IN", "BEEP", "RANDOMIZE", "END", "WEND",
                    "NEW", "EDIT", "LIST", "SAVE", "FILES", "RUN", "CHECK", "HINT",
                    "MODE", "SCREEN", "ADMIN", "CLASS", "BREAK", "REM", "'"
                ]
                if target not in no_arg_cmds and len(parts) < 2 and "=" not in command_line:
                    return False
                
            if require_quotes:
                rest = parts[1] if len(parts) > 1 else ""
                if "=" in command_line:
                    rest = command_line.partition("=")[2]
                if not re.search(r'"[^"]*"|\'[^\']*\'', rest):
                    return False

            # Sprawdzamy czy zadanie wymaga dokładnego wpisania określonej komendy
            # Wyjątek: zadania personalne oraz zadania panelu nauczyciela
            task_id = task.get("id", "")
            if task_id not in ["print_name", "print_age", "print_color"] and not task_id.startswith("teacher_"):
                test_input = task.get("test_input")
                if test_input:
                    norm_user = normalize_code(command_line)
                    if norm_user == "CLR":
                        norm_user = "CLS"
                    if isinstance(test_input, str):
                        if norm_user != normalize_code(test_input):
                            return False
                    elif isinstance(test_input, list):
                        if norm_user not in [normalize_code(t) for t in test_input]:
                            return False

            return True
            
        elif v_type == "counter":
            target_cmd = task["validation"]["target_command"].upper()
            required_count = task["validation"]["required_count"]
            
            # Pobieramy globalną liczbę użyć komendy
            action_counts = user_data.get("action_counts", {})
            current_total = action_counts.get(target_cmd, 0)
            
            task_id = task.get("id")
            if not task_id:
                return current_total >= required_count

            # Zapamiętujemy stan licznika w momencie aktywacji tego zadania w user_data
            if "task_start_counts" not in user_data:
                user_data["task_start_counts"] = {}
                
            if task_id not in user_data["task_start_counts"]:
                user_data["task_start_counts"][task_id] = current_total - 1
                
            start_count = user_data["task_start_counts"][task_id]
            progress = current_total - start_count
            
            return progress >= required_count
            
        return False
