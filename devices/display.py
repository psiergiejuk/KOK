# Wewnątrz głównej pętli w main.py

import time

running = True
exit_requested_time = 0
EXIT_TIMEOUT = 2.0  # Masz 2 sekundy na drugie wciśnięcie ESC

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                current_time = time.time()
                
                # Sprawdzamy, czy użytkownik wcisnął ESC drugi raz w ciągu 2 sekund
                if exit_requested_time and (current_time - exit_requested_time < EXIT_TIMEOUT):
                    running = False
                else:
                    exit_requested_time = current_time
                    print("Wciśnij ESC ponownie, aby wyjść z KOK BASIC.")
                    # Tutaj w przyszłości możemy też wyświetlić napis na ekranie dla dziecka!

    clock.tick(60)
