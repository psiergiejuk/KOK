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
    assert "HELP_1" in user_data["unlocked_techs"]

def test_successful_authentication(temp_user_manager):
    """Testuje poprawne logowanie przy dobrym haśle oraz tolerancję wielkości liter."""
    username = "ola"
    temp_user_manager.register_user(username, "Ola", "Nowak", 10, "tajne123")

    # 1. Dokładne hasło
    logged_user = temp_user_manager.authenticate_user(username, "tajne123")
    assert logged_user is not None
    assert logged_user["first_name"] == "Ola"

    # 2. Tolerancja CapsLock / Mobile (wielkie litery)
    logged_caps = temp_user_manager.authenticate_user(username, "TAJNE123")
    assert logged_caps is not None
    assert logged_caps["username"] == "ola"

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


def test_user_roles_and_teacher_student_limit(temp_user_manager):
    # Nauczyciel i uczeń
    temp_user_manager.register_user("profesor", "Adam", "Belferski", 45, "pass1", role="teacher")
    assert temp_user_manager.get_user_role("profesor") == "teacher"
    assert temp_user_manager.get_teacher_max_students("profesor") == 50

    # Przypisujemy ucznia do nauczyciela
    temp_user_manager.register_user("uczen_1", "Ola", "A", 11, "pass2", role="student", owner_teacher="profesor")
    assert temp_user_manager.get_user_role("uczen_1") == "student"
    assert temp_user_manager.count_teacher_students("profesor") == 1


def test_classes_linux_groups_and_reports(temp_user_manager):
    # Tworzymy nauczyciela oraz 2 klasy
    temp_user_manager.register_user("prof", "Piotr", "N", 38, "pass", role="teacher")
    ok, msg, cls1 = temp_user_manager.create_class("1A", "Klasa 1A", "prof")
    assert ok is True
    ok, msg, cls2 = temp_user_manager.create_class("KOLO_INF", "Kółko Informatyczne", "prof")
    assert ok is True

    # Tworzymy uczniów
    temp_user_manager.register_user("uczen_a", "Ania", "", 10, "pass", role="student", owner_teacher="prof")
    temp_user_manager.register_user("uczen_b", "Bartek", "", 10, "pass", role="student", owner_teacher="prof")
    temp_user_manager.adjust_user_sp("uczen_a", 30)
    temp_user_manager.adjust_user_sp("uczen_b", 10)

    # Uczeń Ania należy do OBU grup (Linux-style multi-group)
    ok, _ = temp_user_manager.add_student_to_class("1A", "uczen_a")
    assert ok is True
    ok, _ = temp_user_manager.add_student_to_class("KOLO_INF", "uczen_a")
    assert ok is True

    # Bartek należy tylko do 1A
    ok, _ = temp_user_manager.add_student_to_class("1A", "uczen_b")
    assert ok is True

    # Weryfikacja przynależności
    ania_classes = temp_user_manager.get_student_classes("uczen_a")
    assert set(ania_classes) == {"1A", "KOLO_INF"}

    # Raport klasy 1A
    rep = temp_user_manager.get_class_report("1A")
    assert rep["students_count"] == 2
    assert rep["avg_sp"] == 20.0  # (30 + 10) / 2
    assert rep["ranking"][0]["username"] == "uczen_a"

    # Wypisanie Bartka z 1A
    ok, _ = temp_user_manager.remove_student_from_class("1A", "uczen_b")
    assert ok is True
    assert "1A" not in temp_user_manager.get_student_classes("uczen_b")


def test_login_authorization_and_license_expiry(temp_user_manager):
    # 1. Samodzielny uczeń bez nauczyciela
    temp_user_manager.register_user("independent_student", "Igor", "", 12, "pass")
    auth_ok, _ = temp_user_manager.is_user_authorized_to_login("independent_student")
    assert auth_ok is True

    # 2. Zablokowany uczeń
    u = temp_user_manager.get_user_summary("independent_student")
    u["is_active"] = 0
    temp_user_manager.save_user_state(u)
    auth_ok, err = temp_user_manager.is_user_authorized_to_login("independent_student")
    assert auth_ok is False
    assert "zablokowane" in err.lower()

    # 3. Uczeń przypisany do nauczyciela z wygasłą licencją
    temp_user_manager.register_user("pan_belferski", "Pan", "B", 50, "pass", role="teacher")
    t_data = temp_user_manager.get_user_summary("pan_belferski")
    t_data["license_expires_at"] = "2020-01-01 00:00:00"  # w przeszłości!
    temp_user_manager.save_user_state(t_data)

    temp_user_manager.register_user("uczen_szkolny", "Krzyś", "", 11, "pass", owner_teacher="pan_belferski")
    # Logowanie ucznia powinno zostać odrzucone z powodu licencji nauczyciela
    s_auth, s_err = temp_user_manager.is_user_authorized_to_login("uczen_szkolny")
    assert s_auth is False
    assert "wygasła" in s_err.lower()

    # Logowanie samego nauczyciela z wygasłą licencją również
    t_auth, t_err = temp_user_manager.is_user_authorized_to_login("pan_belferski")
    assert t_auth is False
    assert "wygasła" in t_err.lower()


def test_remote_tech_manipulation_and_command_log(temp_user_manager):
    temp_user_manager.register_user("zdalny_gracz", "Zdzichu", "", 12, "pass")

    # 1. Odblokowanie pojedynczej technologii
    ok, msg, techs = temp_user_manager.set_user_tech("zdalny_gracz", "FOR_1", add=True)
    assert ok is True
    assert "FOR_1" in techs

    # 2. Zablokowanie technologii
    ok, msg, techs = temp_user_manager.set_user_tech("zdalny_gracz", "FOR_1", add=False)
    assert ok is True
    assert "FOR_1" not in techs

    # 3. Zdalny reset technologii
    ok, msg = temp_user_manager.reset_user_tech("zdalny_gracz")
    assert ok is True
    u = temp_user_manager.get_user_summary("zdalny_gracz")
    assert u["unlocked_techs"] == ["HELP_1"]

    # 4. Zapisywanie komend i pobieranie ostatnich 20
    for i in range(25):
        temp_user_manager.record_user_command("zdalny_gracz", f"PRINT {i}")

    recent = temp_user_manager.get_user_recent_commands("zdalny_gracz", limit=20)
    assert len(recent) == 20
    assert "PRINT 24" in recent[-1]
