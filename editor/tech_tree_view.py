import pygame

class TechTreeView:
    def __init__(self, font):
        self.font = font

    def handle_keydown(self, event, available_techs, user_data):
        """
        Obsługuje klawisze w widoku drzewa technologii.
        Zwraca krotkę (wybrana_technologia, komunikat_błędu).
        """
        # Sprawdzamy klawisze numeryczne 1-9
        if pygame.K_1 <= event.key <= pygame.K_9:
            idx = event.key - pygame.K_1
            if 0 <= idx < len(available_techs):
                chosen_tech = available_techs[idx]
                cost = chosen_tech.get("cost", 0)
                current_sp = user_data.get("science_points", 0)
                
                if current_sp >= cost:
                    return chosen_tech, None
                else:
                    return None, f"❌ Za mało punktów SP! Potrzebujesz {cost} SP, masz tylko {current_sp} SP."
        return None, None

    def draw(self, screen, width, height, available_techs, user_data):
        """Rysuje dedykowany ekran drzewa technologii (nakładka retro)."""
        # Półprzezroczyste tło nakładki
        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        overlay.fill((15, 15, 35, 240))
        screen.blit(overlay, (0, 0))

        # Nagłówek
        title_surf = self.font.render("=== 🔬 DRZEWO TECHNOLOGII - KOK BASIC ===", True, (255, 215, 0))
        screen.blit(title_surf, (50, 80))

        current_sp = user_data.get("science_points", 0)
        sp_surf = self.font.render(f"Twoje Punkty Naukowe (SP): {current_sp}", True, (100, 255, 100))
        screen.blit(sp_surf, (50, 130))

        instruction_surf = self.font.render("Wybierz technologię do odblokowania (wcisnij odpowiedni numer):", True, (200, 200, 220))
        screen.blit(instruction_surf, (50, 180))

        # Lista dostępnych technologii
        y = 240
        for idx, tech in enumerate(available_techs, 1):
            name = tech.get('name', 'Nieznana')
            cost = tech.get('cost', 0)
            
            can_afford = current_sp >= cost
            color = (255, 255, 255) if can_afford else (120, 120, 120)
            
            line = f"  [{idx}] {name}  -->  Koszt: {cost} SP"
            if not can_afford:
                line += " (Brak SP!)"
                
            surf = self.font.render(line, True, color)
            screen.blit(surf, (70, y))
            y += 45

        # Stopka
        footer_surf = self.font.render("Wciśnij odpowiedni cyfrowy klawisz na klawiaturze, aby zatwierdzić zakup.", True, (150, 150, 180))
        screen.blit(footer_surf, (50, height - 80))
