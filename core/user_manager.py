import os
import json
import hashlib

class UserManager:
    """Zarządza rejestracją, logowaniem oraz stanem i zapisem profilu użytkownika."""
    
    def __init__(self, data_dir: str = "data/users"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)

    @property
    def users_dir(self) -> str:
        return self.data_dir

    @users_dir.setter
    def users_dir(self, value: str):
        self.data_dir = value
        os.makedirs(self.data_dir, exist_ok=True)

    def _get_user_filepath(self, username: str) -> str:
        # Bezpieczna nazwa pliku oparta na loginie (małe litery)
        safe_username = username.strip().lower()
        return os.path.join(self.data_dir, f"{safe_username}.json")

    def user_exists(self, username: str) -> bool:
        """Sprawdza, czy profil użytkownika już istnieje."""
        return os.path.exists(self.get_user_filepath(username))

    def get_user_filepath(self, username: str) -> str:
        return self._get_user_filepath(username)

    def _hash_password(self, password: str) -> str:
        """Proste haszowanie hasła (dla celów edukacyjnych/lokalnych)."""
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def register_user(self, username: str, first_name: str, last_name: str, age: int, password: str) -> dict:
        """Tworzy nowy profil użytkownika i zapisuje go w pliku JSON."""
        os.makedirs(self.data_dir, exist_ok=True)
        filepath = self.get_user_filepath(username)
        
        user_data = {
            "username": username.strip(),
            "first_name": first_name.strip(),
            "last_name": last_name.strip(),
            "age": int(age),
            "password_hash": self._hash_password(password),
            "science_points": 0,
            "unlocked_techs": ["PRINT_1"],
            "completed_tasks": [],
            "action_counts": {}
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(user_data, f, ensure_ascii=False, indent=4)
            
        return user_data

    def authenticate_user(self, username: str, password: str) -> dict | None:
        """Weryfikuje hasło i wczytuje dane użytkownika, jeśli poprawne."""
        filepath = self.get_user_filepath(username)
        if not os.path.exists(filepath):
            return None
            
        with open(filepath, "r", encoding="utf-8") as f:
            user_data = json.load(f)
            
        if user_data.get("password_hash") == self._hash_password(password):
            return user_data
            
        return None

    def save_user_state(self, user_data: dict):
        """Zapisuje aktualny stan profilu gracza do pliku."""
        username = user_data.get("username")
        if not username:
            return
        os.makedirs(self.data_dir, exist_ok=True)
        filepath = self.get_user_filepath(username)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(user_data, f, ensure_ascii=False, indent=4)

    def delete_user(self, username: str):
        """Usuwa plik profilu użytkownika (przydatne do testów)."""
        filepath = self.get_user_filepath(username)
        if os.path.exists(filepath):
            os.remove(filepath)
