class QuestValidator:
    @staticmethod
    def validate(task, command_line, user_data) -> bool:
        v_type = task["validation"]["type"]
        
        if v_type == "command_prefix":
            target = task["validation"]["target"].upper()
            require_quotes = task["validation"].get("require_quotes", False)
            
            parts = command_line.strip().split(maxsplit=1)
            if not parts:
                return False
            cmd = parts[0].upper()
            
            if cmd != target:
                return False
                
            if require_quotes:
                rest = parts[1] if len(parts) > 1 else ""
                if not ('"' in rest or "'" in rest):
                    return False
            return True
            
        elif v_type == "counter":
            target_cmd = task["validation"]["target_command"].upper()
            required_count = task["validation"]["required_count"]
            
            # Pobieramy globalną liczbę użyć komendy
            action_counts = user_data.get("action_counts", {})
            current_total = action_counts.get(target_cmd, 0)
            
            # Zapamiętujemy stan licznika w momencie aktywacji tego zadania w user_data
            if "task_start_counts" not in user_data:
                user_data["task_start_counts"] = {}
                
            task_id = task["id"]
            if task_id not in user_data["task_start_counts"]:
                # Od tego momentu zaczynamy liczyć (odejmujemy to, co było wcześniej)
                user_data["task_start_counts"][task_id] = current_total - 1  # -1 bo dzisiejsza komenda właśnie się wykonuje
                
            start_count = user_data["task_start_counts"][task_id]
            progress = current_total - start_count
            
            return progress >= required_count
            
        return False
