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

        tech_dict = {}
        if "technologies" in data:
            for t in data["technologies"]:
                tech_dict[t["id"]] = t

        if "technologies_files" in data:
            base_dir = os.path.dirname(filepath)
            for file_path in data["technologies_files"]:
                full_path = file_path if os.path.isabs(file_path) else os.path.join(base_dir, "..", file_path)
                if not os.path.exists(full_path):
                    full_path = file_path
                if os.path.exists(full_path):
                    with open(full_path, "r", encoding="utf-8") as tf:
                        t_data = json.load(tf)
                        tech_dict[t_data["id"]] = t_data

        return tech_dict
