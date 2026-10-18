# devices/display.py
import pygame

# Retro paleta kolorów (PICO-8 style)
PALETTE = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "red": (255, 0, 77),
    "blue": (41, 173, 255),
    "yellow": (255, 236, 39),
    "green": (0, 228, 54)
}

class DisplayDevice:
    def __init__(self, width=1024, height=768):
        self.width = width
        self.height = height
        
        # Ekran tworzymy tutaj – ta metoda wykona się w main.py PO pygame.init()
        self.screen = pygame.display.set_mode(
            (self.width, self.height), 
            pygame.FULLSCREEN | pygame.SCALED
        )
        pygame.display.set_caption("KOK BASIC")
        self.current_color = PALETTE["white"]

    def clear(self, color_name="black"):
        bg_color = PALETTE.get(color_name, (0, 0, 0))
        self.screen.fill(bg_color)

    def set_color(self, color_name):
        if color_name in PALETTE:
            self.current_color = PALETTE[color_name]

    def draw_circle(self, x, y, radius):
        pygame.draw.circle(self.screen, self.current_color, (x, y), radius)

    def update(self):
        pygame.display.flip()
