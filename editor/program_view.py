# editor/program_view.py
import pygame

class ProgramView:
    def __init__(self, model):
        self.model = model
        self.font = pygame.font.SysFont("Courier", 24)

    def draw(self, surface):
        """Rysuje zapisane linijki programu BASIC od góry ekranu"""
        y_offset = 40
        for line_num, code in sorted(self.model.lines.items()):
            text_surf = self.font.render(f"{line_num} {code}", True, (255, 255, 255))
            surface.blit(text_surf, (40, y_offset))
            y_offset += 30
