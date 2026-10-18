# main.py
import pygame
from core.model import ProgramModel
from core.interpreter import Interpreter
from devices.display import DisplayDevice

def main():
    pygame.init()  # <-- NAJPIERW INICJALIZACJA SYSTEMU PYGAME
    
    # POTEM TWORZYMY URZĄDZENIA (dzięki temu system wideo jest już gotowy)
    display = DisplayDevice(1024, 768)
    model = ProgramModel()
    interpreter = Interpreter(model, display)

    model.set_line(10, "COLOR yellow")
    model.set_line(20, "CIRCLE 512, 384, 100")

    display.clear("black")
    interpreter.run_program()
    display.update()

    clock = pygame.time.Clock()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
