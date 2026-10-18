# main.py
import pygame
import time
from core.model import ProgramModel
from core.interpreter import Interpreter
from devices.display import DisplayDevice
from editor.program_view import ProgramView
from editor.console import Console

def main():
    pygame.init()
    
    display = DisplayDevice(1024, 768)
    model = ProgramModel()
    interpreter = Interpreter(model, display)
    
    # Osobne moduły edycji i konsoli
    program_view = ProgramView(model)
    console = Console(model)

    clock = pygame.time.Clock()
    running = True
    exit_requested_time = 0

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    current_time = time.time()
                    if exit_requested_time and (current_time - exit_requested_time < 2.0):
                        running = False
                    else:
                        exit_requested_time = current_time
                        print("Wciśnij ESC ponownie, aby wyjść.")
                else:
                    # Zdarzenia klawiatury idą bezpośrednio do konsoli
                    console.handle_event(event)

        # Rysowanie klatki
        display.clear("black")
        
        program_view.draw(display.screen)
        console.draw(display.screen)
        
        display.update()
        clock.tick(60)

    pygame.quit()

if __name__ == "__main__":
    main()
