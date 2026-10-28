import pygame
import sys
from editor.console import RetroConsoleManager

def main():
    pygame.init()
    
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    WIDTH, HEIGHT = screen.get_size()
    pygame.display.set_caption("KOK BASIC - Edukacyjny Emulator")
    
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Courier New", 24)
    
    console_manager = RetroConsoleManager(font)

    running = True
    while running:
        screen.fill((15, 15, 35))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if not console_manager.handle_keydown(event):
                    running = False

        console_manager.draw(screen, WIDTH, HEIGHT)

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
