class PlayerState:
    """Zarządza stanem gracza: punktami nauki (SP), odblokowanymi technologiami i postępami."""
    
    def __init__(self):
        self.science_points = 0
        self.unlocked_techs = []
        self.completed_tasks = []
        self.action_counts = {}

    def has_tech(self, tech_id: str) -> bool:
        """Sprawdza, czy technologia została odblokowana."""
        return tech_id in self.unlocked_techs

    def try_unlock(self, tech_id: str, tech_config: dict) -> bool:
        """Próbuje odblokować technologią, sprawdzając punkty i wymagania (requires)."""
        cost = tech_config.get("cost", 0)
        requires = tech_config.get("requires", [])
        
        if self.has_tech(tech_id):
            return False
            
        if self.science_points < cost:
            return False
            
        for req in requires:
            if not self.has_tech(req):
                return False
                
        # Odblokowanie
        self.science_points -= cost
        self.unlocked_techs.append(tech_id)
        return True
