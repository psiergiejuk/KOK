import pytest
import pygame
from unittest.mock import MagicMock
from editor.console import RetroConsoleManager

@pytest.fixture(autouse=True)
def init_pygame():
    """Inicjalizuje moduł fontów Pygame przed każdym testem."""
    pygame.font.init()
    yield
    pygame.font.quit()

@pytest.fixture
def console_manager(tmp_path):
    """Tworzy instancję RetroConsoleManager z całkowicie czystą, odizolowaną bazą użytkowników."""
    mock_font = MagicMock()
    mock_font.render.return_value = MagicMock()
    
    from core.user_manager import UserManager
    user_mgr = UserManager(data_dir=str(tmp_path / "users"))
    console = RetroConsoleManager(mock_font, user_manager=user_mgr)
    return console

def create_key_event(key, unicode_char=""):
    """Pomocnicza funkcja do tworzenia zdarzeń naciskania klawisza Pygame."""
    return pygame.event.Event(pygame.KEYDOWN, key=key, unicode=unicode_char)


# --- TESTY EDYCJI TEKSTU I KURSORA ---

def test_cursor_navigation_and_typing(console_manager):
    """Testuje pisanie, przesuwanie kursora w lewo/prawo oraz wstawianie znaków w środek tekstu."""
    for char in "TEST":
        console_manager.handle_keydown(create_key_event(0, unicode_char=char))
    
    assert console_manager.input_text == "TEST"
    assert console_manager.cursor_pos == 4

    # Przesuwamy kursor w lewo o 2 pozycje (kursor pod 'S')
    console_manager.handle_keydown(create_key_event(pygame.K_LEFT))
    console_manager.handle_keydown(create_key_event(pygame.K_LEFT))
    assert console_manager.cursor_pos == 2

    # Wstawiamy literę 'X' -> "TEXST"
    console_manager.handle_keydown(create_key_event(0, unicode_char="X"))
    assert console_manager.input_text == "TEXST"
    assert console_manager.cursor_pos == 3

def test_backspace_and_delete(console_manager):
    """Testuje usuwanie znaków klawiszami Backspace oraz Delete."""
    for char in "KOK":
        console_manager.handle_keydown(create_key_event(0, unicode_char=char))
        
    # Kursor na końcu "KOK" -> Backspace usuwa 'K'
    console_manager.handle_keydown(create_key_event(pygame.K_BACKSPACE))
    assert console_manager.input_text == "KO"
    assert console_manager.cursor_pos == 2

    # Przesuwamy kursor na początek
    console_manager.handle_keydown(create_key_event(pygame.K_LEFT))
    console_manager.handle_keydown(create_key_event(pygame.K_LEFT))
    assert console_manager.cursor_pos == 0

    # Kursor przed 'K' -> Delete usuwa 'K' -> zostaje "O"
    console_manager.handle_keydown(create_key_event(pygame.K_DELETE))
    assert console_manager.input_text == "O"


# --- TESTY MASZYNY STANÓW (REJESTRACJA I LOGOWANIE) ---

def test_full_registration_flow(console_manager):
    """Testuje pełny proces tworzenia nowego konta użytkownika."""
    assert console_manager.current_state == console_manager.STATE_USERNAME

    # 1. Podanie nazwy użytkownika (unikalna nazwa)
    for char in "nowy_super_gracz":
        console_manager.handle_keydown(create_key_event(0, unicode_char=char))
    console_manager.handle_keydown(create_key_event(pygame.K_RETURN))
    assert console_manager.current_state == console_manager.STATE_CONFIRM_REGISTER

    # 1b. Potwierdzenie chęci utworzenia nowego konta (T)
    console_manager.handle_keydown(create_key_event(0, unicode_char="T"))
    console_manager.handle_keydown(create_key_event(pygame.K_RETURN))
    assert console_manager.current_state == console_manager.STATE_REG_FIRST

    # 2. Podanie imienia
    for char in "Jan":
        console_manager.handle_keydown(create_key_event(0, unicode_char=char))
    console_manager.handle_keydown(create_key_event(pygame.K_RETURN))
    assert console_manager.current_state == console_manager.STATE_REG_LAST

    # 3. Podanie nazwiska
    for char in "Kowalski":
        console_manager.handle_keydown(create_key_event(0, unicode_char=char))
    console_manager.handle_keydown(create_key_event(pygame.K_RETURN))
    assert console_manager.current_state == console_manager.STATE_REG_AGE

    # 4. Podanie wieku
    for char in "10":
        console_manager.handle_keydown(create_key_event(0, unicode_char=char))
    console_manager.handle_keydown(create_key_event(pygame.K_RETURN))
    assert console_manager.current_state == console_manager.STATE_REG_PASS

    # 5. Podanie hasła po raz pierwszy
    for char in "tajne123":
        console_manager.handle_keydown(create_key_event(0, unicode_char=char))
    console_manager.handle_keydown(create_key_event(pygame.K_RETURN))
    assert console_manager.current_state == console_manager.STATE_REG_PASS_CONFIRM

    # 5b. Powtórzenie hasła
    for char in "tajne123":
        console_manager.handle_keydown(create_key_event(0, unicode_char=char))
    console_manager.handle_keydown(create_key_event(pygame.K_RETURN))

    # Po rejestracji przechodzimy do konsoli
    assert console_manager.current_state == console_manager.STATE_CONSOLE
    assert console_manager.user_data["username"] == "nowy_super_gracz"
    assert console_manager.user_data["first_name"] == "Jan"


# --- TESTY OBSŁUGI KOMEND W KONSOLI ---

def test_console_print_syntax_error(console_manager):
    """Testuje zwrócenie SYNTAX ERROR w konsoli przy próbie wypisania niezdefiniowanej zmiennej / tekstu bez cudzysłowu."""
    console_manager.current_state = console_manager.STATE_CONSOLE
    console_manager.user_data = {
        "username": "test_user",
        "science_points": 0,
        "completed_tasks": [],
        "action_counts": {}
    }

    # Wpisujemy błędną komendę "PRINT ja"
    for char in 'PRINT ja':
        console_manager.handle_keydown(create_key_event(0, unicode_char=char))
    console_manager.handle_keydown(create_key_event(pygame.K_RETURN))

    # Ostatnia linia konsoli powinna informować o błędzie składni
    assert "SYNTAX ERROR: Niezdefiniowana zmienna lub brak cudzysłowu" in console_manager.console_lines[-1]

def test_reset_confirmation(console_manager):
    """Testuje przejście do stanu potwierdzenia resetu profilu po komendzie _RESET."""
    console_manager.current_state = console_manager.STATE_CONSOLE
    console_manager.user_data = {"username": "test_user"}

    # Wpisujemy komendę "_RESET"
    for char in '_RESET':
        console_manager.handle_keydown(create_key_event(0, unicode_char=char))
    console_manager.handle_keydown(create_key_event(pygame.K_RETURN))

    # Zmiana stanu na CONFIRM_RESET
    assert console_manager.current_state == console_manager.STATE_CONFIRM_RESET

    # Anulowanie resetu (wpisujemy "N")
    console_manager.handle_keydown(create_key_event(0, unicode_char="N"))
    console_manager.handle_keydown(create_key_event(pygame.K_RETURN))

    # Powrót do konsoli
    assert console_manager.current_state == console_manager.STATE_CONSOLE
