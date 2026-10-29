import pytest
from core.quest_validator import QuestValidator

def test_quest_validator_strict_input():
    task_math = {
        "id": "math_1",
        "validation": {"type": "command_prefix", "target": "PRINT"},
        "test_input": "PRINT 2 + 2"
    }

    # Błędne wpisy nie mogą zaliczyć zadania
    assert QuestValidator.validate(task_math, "PRINT 2 + 3", {}) is False
    assert QuestValidator.validate(task_math, "PRINT 4", {}) is False
    assert QuestValidator.validate(task_math, "CLS", {}) is False

    # Poprawne wpisy (z różnymi spacjami / wielkością liter) zaliczają
    assert QuestValidator.validate(task_math, "PRINT 2 + 2", {}) is True
    assert QuestValidator.validate(task_math, "print 2+2", {}) is True
    assert QuestValidator.validate(task_math, "PRINT   2  +  2", {}) is True


def test_command_prefix_valid():
    """Testuje poprawność wykrywania komendy z argumentem."""
    task = {
        "validation": {
            "type": "command_prefix",
            "target": "PRINT"
        }
    }
    assert QuestValidator.validate(task, 'PRINT "CZEŚĆ"', {}) is True

def test_command_prefix_invalid_no_argument():
    """Testuje odrzucenie komendy PRINT bez argumentu."""
    task = {
        "validation": {
            "type": "command_prefix",
            "target": "PRINT"
        }
    }
    assert QuestValidator.validate(task, "PRINT", {}) is False
    assert QuestValidator.validate(task, "print ", {}) is False

def test_counter_validation():
    """Testuje zliczanie akcji na podstawie stanu gracza."""
    task = {
        "validation": {
            "type": "counter",
            "target_command": "PRINT",
            "required_count": 2
        }
    }
    player_state_low = {"action_counts": {"PRINT": 1}}
    assert QuestValidator.validate(task, 'PRINT "A"', player_state_low) is False

    player_state_ok = {"action_counts": {"PRINT": 2}}
    assert QuestValidator.validate(task, 'PRINT "B"', player_state_ok) is True

def test_require_quotes_matching():
    """Testuje, że zadanie wymagające cudzysłowu odrzuca niedomknięty cudzysłów."""
    task = {
        "id": "print_color",
        "validation": {
            "type": "command_prefix",
            "target": "PRINT",
            "require_quotes": True
        }
    }
    # Poprawnie domknięty cudzysłów
    assert QuestValidator.validate(task, 'PRINT "ZIELONY"', {}) is True
    assert QuestValidator.validate(task, "PRINT 'NIEBIESKI'", {}) is True

    # Niedomknięty cudzysłów (tylko 1 cudzysłów na początku)
    assert QuestValidator.validate(task, 'PRINT "ZIELONY', {}) is False
    assert QuestValidator.validate(task, "PRINT 'ZIELONY", {}) is False

    # Całkowity brak cudzysłowu
    assert QuestValidator.validate(task, 'PRINT ZIELONY', {}) is False


def test_dynamic_plugin_missing_safely():
    """Testuje, czy moduł bezpiecznie obsługuje brak wtyczki."""
    task = {
        "validation": {
            "type": "dynamic_plugin",
            "module_path": "plugins.nie_istniejacy_modul",
            "function_name": "verify"
        }
    }
    assert QuestValidator.validate(task, "jakas akcja", {}) is False


def test_all_tech_tree_tasks_automation():
    """Automatycznie weryfikuje wszystkie 216 zadań ze wszystkich technologii bez zależności od Pygame."""
    import json
    import os

    root_cfg_path = "config/tech_tree.json"
    with open(root_cfg_path, "r", encoding="utf-8") as f:
        root_cfg = json.load(f)

    tasks = []
    for file_path in root_cfg.get("technologies_files", []):
        with open(file_path, "r", encoding="utf-8") as tf:
            tech_data = json.load(tf)
            for t in tech_data.get("tasks", []):
                t_copy = dict(t)
                t_copy["tech_id"] = tech_data["id"]
                tasks.append(t_copy)

    user_data = {
        "username": "tester",
        "first_name": "Test",
        "science_points": 0,
        "completed_tasks": [],
        "unlocked_techs": [t.get("tech_id") for t in tasks],
        "action_counts": {},
        "task_start_counts": {}
    }

    for task in tasks:
        test_inputs = task.get("test_input")
        if not test_inputs:
            continue
        if isinstance(test_inputs, str):
            test_inputs = [test_inputs]

        for cmd in test_inputs:
            cmd_name = cmd.split()[0].upper()
            user_data["action_counts"][cmd_name] = user_data["action_counts"].get(cmd_name, 0) + 1

            if task.get("validation", {}).get("type") == "counter":
                target_cmd = task["validation"].get("target_command", "").upper()
                user_data["action_counts"][target_cmd] = user_data["action_counts"].get(target_cmd, 0) + 1

            if QuestValidator.validate(task, cmd, user_data):
                if task["id"] not in user_data["completed_tasks"]:
                    reward = task.get("reward_sp", 1)
                    user_data["science_points"] += reward
                    user_data["completed_tasks"].append(task["id"])

    assert len(tasks) == 221
    assert len(user_data["completed_tasks"]) == 221

