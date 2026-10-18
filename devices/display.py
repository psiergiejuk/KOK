# devices/display.py
import pygame

# Stała, retro paleta kolorów (jak w PICO-8)
PALETTE = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "red": (255, 0, 77),
    "blue": (41, 173, 255),
    "yellow": (255, 236, 39),
    "green": (0, 228, 54)
}

class DisplayDevice:
    def __init__(self, width=800, height=600):
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((self.width, self.height))
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
