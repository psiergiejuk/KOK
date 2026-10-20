import os
import pytest
from core.user_manager import UserManager

@pytest.fixture
def temp_user_manager(tmp_path):
    """Tworzy UserManager korzystający z tymczasowego katalogu na czas testów."""
    return UserManager(data_dir=str(tmp_path / "users"))

def test_user_registration_and_exists(temp_user_manager):
    """Testuje rejestrację nowego użytkownika oraz wykrywanie jego istnienia."""
    username = "siergiej"
    assert temp_user_manager.user_exists(username) is False
    
    user_data = temp_user_manager.register_user(
        username=username,
        first_name="Siergiej",
        last_name="K",
        age=12,
        password="tajnehaslo123"
    )
    
    assert temp_user_manager.user_exists(username) is True
    assert user_data["science_points"] == 0
    assert "PRINT_1" in user_data["unlocked_techs"]

def test_successful_authentication(temp_user_manager):
    """Testuje poprawne logowanie przy dobrym haśle."""
    username = "ola"
    temp_user_manager.register_user(username, "Ola", "Nowak", 10, "1234")
    
    logged_user = temp_user_manager.authenticate_user(username, "1234")
    assert logged_user is not None
    assert logged_user["first_name"] == "Ola"

def test_failed_authentication_wrong_password(temp_user_manager):
    """Testuje odrzucenie logowania przy błędnym haśle."""
    username = "ola"
    temp_user_manager.register_user(username, "Ola", "Nowak", 10, "1234")
    
    logged_user = temp_user_manager.authenticate_user(username, "zlehaslo")
    assert logged_user is None

def test_delete_user(temp_user_manager):
    """Testuje usuwanie profilu użytkownika."""
    username = "skaner"
    assert temp_user_manager.user_exists(username) is False
    
    # Rejestrujemy użytkownika
    temp_user_manager.register_user(
        username=username,
        first_name="Jan",
        last_name="Kowalski",
        age=15,
        password="haslo"
    )
    assert temp_user_manager.user_exists(username) is True
    
    # Usuwamy użytkownika
    temp_user_manager.delete_user(username)
    assert temp_user_manager.user_exists(username) is False
