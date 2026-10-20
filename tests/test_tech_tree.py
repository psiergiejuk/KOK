import pytest
from core.tech_tree import TechTreeLoader  # Załóżmy taki moduł do ładowania JSON-a

def test_tech_tree_loading():
    """Testuje czy konfiguracja technologii wczytuje się bez błędów i zawiera startowe węzły."""
    # Przykładowe załadowanie drzewa (można wskazać plik testowy lub mock)
    tree = TechTreeLoader.load_from_json("config/tech_tree.json")
    
    assert "PRINT_1" in tree
    assert "CLS" in tree
    
    # Sprawdzenie zależności (CLS wymaga PRINT_1)
    cls_node = tree["CLS"]
    assert "PRINT_1" in cls_node["requires"]
    assert cls_node["cost"] >= 0


def test_tech_tree_dag_integrity():
    """Sprawdza czy w grafie technologii nie ma błędnych odnośników do nieistniejących wymagań."""
    tree = TechTreeLoader.load_from_json("config/tech_tree.json")
    all_ids = set(tree.keys())
    
    for tech_id, data in tree.items():
        for req in data.get("requires", []):
            assert req in all_ids, f"Technologia {tech_id} wymaga nieistniejącego węzła: {req}"
