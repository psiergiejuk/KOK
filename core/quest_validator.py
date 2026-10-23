import re

def normalize_code(s: str) -> str:
    """Normalizuje komendę: wielkie litery, redukcja spacji, usunięcie spacji wokół operatorów."""
    s = re.sub(r'\s+', ' ', s.strip().upper())
    s = re.sub(r'\s*([=+\-*/(),])\s*', r'\1', s)
    return s

class QuestValidator:
    @staticmethod
    def validate(task, command_line, user_data) -> bool:
        v_type = task["validation"]["type"]

        if v_type == "exit_restart":
            return command_line.strip().upper() == "EXIT"
        
        elif v_type == "command_prefix":
            target = task["validation"]["target"].upper()
            require_quotes = task["validation"].get("require_quotes", False)
            
            parts = command_line.strip().split(maxsplit=1)
            if not parts:
                return False
            cmd = parts[0].upper()
            
            # Obsługa przypisań bez spacji, np. A=5 gdy target to "A"
            if "=" in parts[0] and not parts[0].upper().startswith("LET"):
                cmd = parts[0].split("=")[0].strip().upper()

            if cmd != target:
                return False
                
            # Komendy oczekujące argumentów (np. PRINT) nie mogą być puste
            if target not in ["CLS", "EXIT"] and len(parts) < 2 and "=" not in command_line:
                return False
                
            if require_quotes:
                rest = parts[1] if len(parts) > 1 else ""
                if "=" in command_line:
                    rest = command_line.partition("=")[2]
                if not ('"' in rest or "'" in rest):
                    return False

            # Sprawdzamy czy zadanie wymaga dokładnego wpisania określonej komendy
            # Wyjątek: zadania personalne z print_1 (imię, wiek, kolor) pozwalają na wpisanie własnych danych
            task_id = task.get("id", "")
            if task_id not in ["print_name", "print_age", "print_color"]:
                test_input = task.get("test_input")
                if test_input:
                    norm_user = normalize_code(command_line)
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
