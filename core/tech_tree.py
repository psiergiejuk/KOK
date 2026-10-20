import json
import os

class TechTreeLoader:
    """Odpowiada za ładowanie i parsowanie struktury drzewa technologii z pliku konfiguracyjnego."""
    
    @staticmethod
    def load_from_json(filepath: str) -> dict:
        """Wczytuje plik JSON i zwraca słownik technologii mapowany po ich ID."""
        if not os.path.exists(filepath):
            return {}
            
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            techs = data.get("technologies", [])
            return {t["id"]: t for t in techs}
