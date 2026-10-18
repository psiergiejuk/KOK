# commands/circle.py

def execute(model, display, args):
    # Oczekiwane argumenty: x, y, promień (np. CIRCLE 100, 100, 30)
    try:
        x = int(args[0])
        y = int(args[1])
        radius = int(args[2])
        display.draw_circle(x, y, radius)
    except (IndexError, ValueError):
        print("Błąd w komendzie CIRCLE: podaj poprawne współrzędne x, y, r")
