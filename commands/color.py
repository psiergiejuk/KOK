# commands/color.py

def execute(model, display, args):
    # Oczekiwany argument: nazwa koloru (np. COLOR yellow)
    if args:
        color_name = args[0].lower()
        display.set_color(color_name)
    else:
        print("Błąd w komendzie COLOR: podaj nazwę koloru")
