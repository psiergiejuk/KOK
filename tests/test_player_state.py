import pytest
from core.player_state import PlayerState

def test_player_initial_state():
    """Gracz zaczyna z zerem punktów i odblokowanym tylko startowym Tierem."""
    player = PlayerState()
    player.science_points = 0
    player.unlocked_techs = ["PRINT_1"]
    
    assert player.has_tech("PRINT_1") is True
    assert player.has_tech("CLS") is False


def test_unlock_technology_success():
    """Testuje poprawne odblokowanie technologii po spełnieniu kosztów i wymagań."""
    player = PlayerState()
    player.science_points = 5  # Gracz ma punkty
    player.unlocked_techs = ["PRINT_1"]
    
    # Definicja technologii CLS (koszt: 1 SP, wymaga PRINT_1)
    cls_config = {"cost": 1, "requires": ["PRINT_1"]}
    
    success = player.try_unlock("CLS", cls_config)
    
    assert success is True
    assert player.science_points == 4 #koszty zostały odliczone
    assert player.has_tech("CLS") is True


def test_unlock_technology_fails_due_to_points():
    """Testuje odrzucenie odblokowania, gdy gracz ma za mało punktów nauki."""
    player = PlayerState()
    player.science_points = 0  # Brak punktów
    player.unlocked_techs = ["PRINT_1"]
    
    cls_config = {"cost": 2, "requires": ["PRINT_1"]}
    success = player.try_unlock("CLS", cls_config)
    
    assert success is False
    assert player.has_tech("CLS") is False
