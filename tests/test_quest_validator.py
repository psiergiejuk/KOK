import pytest
from core.quest_validator import QuestValidator

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
