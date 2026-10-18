# main.py
import pygame
from core.model import ProgramModel
from core.interpreter import Interpreter
from devices.display import DisplayDevice

def main():
    pygame.init()
    
    # Inicjalizacja komponentów
    display = DisplayDevice(1024, 768)
    model = ProgramModel()
    interpreter = Interpreter(model, display)

    # Przykładowy testowy kod wrzucony do modelu
    model.set_line(10, "COLOR yellow")
    model.set_line(20, "CIRCLE 512, 384, 100")

    clock = pygame.time.Clock()
    running = True

    # Tymczasowe uruchomienie programu na start
    display.clear("black")
    interpreter.run_program()
    display.update()

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running =jaer = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False # Wyjście pod ESC

        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
