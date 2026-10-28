import array
import math
import pygame


def play_retro_victory_sound():
    """Generuje i odtwarza retro dźwięk w stylu Pegasusa/chiptune."""
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=22050, size=-16, channels=1)
        sample_rate = 22050

        def make_tone(freq, duration):
            num_samples = int(sample_rate * duration)
            buf = array.array(
                "h",
                [int(32767 * 0.3 * math.sin(2 * math.pi * freq * i / sample_rate)) for i in range(num_samples)],
            )
            return pygame.mixer.Sound(buffer=buf)

        for f in [523.25, 659.25, 783.99, 1046.50]:
            s = make_tone(f, 0.08)
            s.play()
            pygame.time.delay(70)
    except Exception:
        pass


def play_retro_fail_sound():
    """Generuje i odtwarza retro dźwięk porażki w stylu Mario/Pegasusa (opadające tony)."""
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=22050, size=-16, channels=1)
        sample_rate = 22050

        def make_tone(freq, duration):
            num_samples = int(sample_rate * duration)
            buf = array.array(
                "h",
                [int(32767 * 0.3 * math.sin(2 * math.pi * freq * i / sample_rate)) for i in range(num_samples)],
            )
            return pygame.mixer.Sound(buffer=buf)

        for f, d in [(493.88, 0.09), (466.16, 0.09), (440.00, 0.09), (392.00, 0.14), (311.13, 0.22)]:
            s = make_tone(f, d)
            s.play()
            pygame.time.delay(int(d * 900))
    except Exception:
        pass


RETRO_ICON_MAP = {
    "\ufe0f": "",
    "🎓": "☼",
    "🤖": "☻",
    "👽": "☻",
    "☕": "☼",
    "⭐": "♦",
    "🌟": "♦",
    "✨": "♦",
    "🎯": "►",
    "🧠": "♦",
    "💡": "☼",
    "💬": "»",
    "🗺": "♦",
    "🔄": "«»",
    "🕒": "☼",
    "⏰": "☼",
    "⏳": "☼",
    "📅": "☼",
    "✅": "[OK]",
    "❌": "[X]",
    "⚠": "[!]",
    "🔒": "[#]",
    "🔓": "[+]",
    "🎉": "☼",
    "🎵": "♫",
    "🎶": "♫",
    "🔊": "♫",
    "▶": "►",
    "▸": "►",
    "⏩": "►",
    "⏹": "■",
    "⭕": "●",
    "⚫": "●",
    "⬜": "■",
    "📏": "■",
    "🔤": "[A]",
    "📄": "■",
    "📝": "■",
    "💾": "■",
    "📂": "■",
    "📦": "■",
    "🔌": "♦",
    "🔬": "♦",
    "🧹": "♦",
    "🗑": "♦",
    "🍕": "♦",
    "🛸": "♦",
    "🧦": "♦",
    "🚨": "‼",
    "🚀": "▲",
    "🥔": "●",
    "🕺": "♪",
    "🎨": "♦",
}


def sanitize_retro_text(text: str) -> str:
    """Zamienia nowoczesne emoji na klasyczne znaki retro CP437 obsługiwane przez czcionkę konsoli."""
    if not text:
        return ""
    out = []
    for ch in str(text):
        if ch in RETRO_ICON_MAP:
            out.append(RETRO_ICON_MAP[ch])
        elif ord(ch) > 0x266B:
            out.append("♦")
        else:
            out.append(ch)
    return "".join(out)


class _RetroFontWrapper:
    """Opakowuje czcionkę Pygame tak, aby automatycznie zamieniać nieobsługiwane ikony przed renderowaniem."""

    def __init__(self, base_font):
        self._base = base_font

    def render(self, text, antialias, color, *args, **kwargs):
        return self._base.render(sanitize_retro_text(text), antialias, color, *args, **kwargs)

    def size(self, text):
        return self._base.size(sanitize_retro_text(text))

    def __getattr__(self, name):
        return getattr(self._base, name)


def wrap_text(text: str, font, max_width: int) -> list[str]:
    """Dzieli długi tekst na linijki tak, aby zmieścił się w zadanej szerokości w pikselach."""
    clean_text = sanitize_retro_text(text)
    if not clean_text:
        return [""]
    words = clean_text.split()
    if not words:
        return [clean_text]
    lines = []
    current_line = []
    for word in words:
        test_line = " ".join(current_line + [word])
        try:
            w = font.size(test_line)[0]
            if not isinstance(w, (int, float)):
                w = len(test_line) * 10
        except Exception:
            w = len(test_line) * 10
        if w <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []
    if current_line:
        lines.append(" ".join(current_line))
    return lines


class CRTChassisRenderer:
    """Odpowiada za budowę obudowy 3D monitora CRT, panelu diod LED/GPIO oraz warstwy graficznej VGA."""

    @staticmethod
    def build_chassis_surface(
        width: int,
        height: int,
        margin_x: int,
        margin_top: int,
        screen_w: int,
        screen_h: int,
        panel_height: int,
        model_font,
        gpio_num_font,
    ):
        """Buduje realistyczną, trójwymiarową obudowę monitora CRT z lat 80."""
        surf = pygame.Surface((width, height))
        surf.fill((18, 20, 26))

        outer_pad = 10
        body_rect = pygame.Rect(outer_pad, outer_pad, width - outer_pad * 2, height - outer_pad * 2)
        pygame.draw.rect(surf, (8, 10, 14), body_rect.move(0, 4), border_radius=26)
        pygame.draw.rect(surf, (192, 186, 170), body_rect, border_radius=24)

        highlight_rect = pygame.Rect(outer_pad + 4, outer_pad + 2, width - (outer_pad + 4) * 2, 18)
        pygame.draw.rect(surf, (224, 218, 204), highlight_rect, border_radius=12)

        bottom_shadow_rect = pygame.Rect(outer_pad + 4, height - outer_pad - 14, width - (outer_pad + 4) * 2, 12)
        pygame.draw.rect(surf, (135, 128, 114), bottom_shadow_rect, border_radius=10)
        pygame.draw.rect(surf, (110, 105, 92), body_rect, width=3, border_radius=24)

        for vent_y in range(margin_top + 30, margin_top + screen_h - 30, 14):
            pygame.draw.line(surf, (115, 110, 98), (14, vent_y), (22, vent_y), 3)
            pygame.draw.line(surf, (215, 210, 196), (14, vent_y + 2), (22, vent_y + 2), 1)
            pygame.draw.line(surf, (115, 110, 98), (width - 22, vent_y), (width - 14, vent_y), 3)
            pygame.draw.line(surf, (215, 210, 196), (width - 22, vent_y + 2), (width - 14, vent_y + 2), 1)

        bevel = 22
        ix1, iy1 = margin_x, margin_top
        ix2, iy2 = margin_x + screen_w, margin_top + screen_h
        ox1, oy1 = ix1 - bevel, iy1 - bevel
        ox2, oy2 = ix2 + bevel, iy2 + bevel

        pygame.draw.polygon(surf, (132, 126, 112), [(ox1, oy1), (ox2, oy1), (ix2, iy1), (ix1, iy1)])
        pygame.draw.polygon(surf, (172, 166, 152), [(ox1, oy1), (ix1, iy1), (ix1, iy2), (ox1, oy2)])
        pygame.draw.polygon(surf, (152, 146, 132), [(ix2, iy1), (ox2, oy1), (ox2, oy2), (ix2, iy2)])
        pygame.draw.polygon(surf, (216, 210, 195), [(ix1, iy2), (ix2, iy2), (ox2, oy2), (ox1, oy2)])

        for p_out, p_in in [((ox1, oy1), (ix1, iy1)), ((ox2, oy1), (ix2, iy1)), ((ox1, oy2), (ix1, iy2)), ((ox2, oy2), (ix2, iy2))]:
            pygame.draw.line(surf, (115, 110, 98), p_out, p_in, 2)

        outer_bezel_rect = pygame.Rect(ox1, oy1, ox2 - ox1, oy2 - oy1)
        pygame.draw.rect(surf, (110, 105, 94), outer_bezel_rect, width=2, border_radius=8)
        pygame.draw.line(surf, (225, 220, 206), (ox1 + 4, oy2 + 1), (ox2 - 4, oy2 + 1), 2)

        panel_y = oy2 + 8
        panel_h = panel_height - 12
        panel_rect = pygame.Rect(ox1, panel_y, ox2 - ox1, panel_h)

        pygame.draw.rect(surf, (125, 120, 108), panel_rect.move(0, 2), border_radius=8)
        pygame.draw.rect(surf, (174, 168, 154), panel_rect, border_radius=8)
        pygame.draw.line(surf, (215, 210, 196), (ox1 + 6, panel_y + 1), (ox2 - 6, panel_y + 1), 2)
        pygame.draw.rect(surf, (115, 110, 98), panel_rect, width=2, border_radius=8)

        badge_rect = pygame.Rect(margin_x + 10, panel_y + 8, 315, panel_h - 16)
        pygame.draw.rect(surf, (45, 42, 38), badge_rect, border_radius=4)
        pygame.draw.rect(surf, (130, 125, 112), badge_rect, width=1, border_radius=4)
        for rx, ry in [
            (badge_rect.left + 5, badge_rect.top + 5),
            (badge_rect.right - 5, badge_rect.top + 5),
            (badge_rect.left + 5, badge_rect.bottom - 5),
            (badge_rect.right - 5, badge_rect.bottom - 5),
        ]:
            pygame.draw.circle(surf, (160, 155, 140), (rx, ry), 2)

        brand_surf = model_font.render("KOK-88 EDUCATIONAL MICROCOMPUTER", True, (220, 210, 185))
        surf.blit(brand_surf, (badge_rect.left + 16, badge_rect.centery - brand_surf.get_height() // 2))

        pwr_btn_rect = pygame.Rect(ox2 - 58, panel_y + 8, 42, panel_h - 16)
        pygame.draw.rect(surf, (60, 58, 54), pwr_btn_rect.move(0, 2), border_radius=5)
        pygame.draw.rect(surf, (200, 75, 50), pwr_btn_rect, border_radius=5)
        pygame.draw.line(surf, (245, 130, 100), (pwr_btn_rect.left + 4, pwr_btn_rect.top + 2), (pwr_btn_rect.right - 4, pwr_btn_rect.top + 2), 2)
        pygame.draw.rect(surf, (90, 35, 25), pwr_btn_rect, width=2, border_radius=5)
        pwr_txt = gpio_num_font.render("I/O", True, (255, 235, 220))
        surf.blit(pwr_txt, (pwr_btn_rect.centerx - pwr_txt.get_width() // 2, pwr_btn_rect.centery - pwr_txt.get_height() // 2))

        return surf

    @staticmethod
    def draw_vga_layer(console_mgr, crt_surf, screen_w: int, screen_h: int, hud_height: int):
        gfx_items = getattr(console_mgr.command_registry, "graphics_items", [])
        if not gfx_items:
            return
        reg = getattr(console_mgr, "command_registry", None)
        mode_w, mode_h = reg.get_mode_dimensions() if reg and hasattr(reg, "get_mode_dimensions") else (120, 80)
        canvas_h = max(100, screen_h - hud_height - 42)
        scale_x = screen_w / max(1, mode_w)
        scale_y = canvas_h / max(1, mode_h)

        for item in gfx_items:
            itype = item.get("type")
            col = item.get("color", (80, 255, 120))
            if itype == "pixel":
                px = int(item["x"] * scale_x)
                py = hud_height + int(item["y"] * scale_y)
                pw = max(1, int(round(scale_x)))
                ph = max(1, int(round(scale_y)))
                pygame.draw.rect(crt_surf, col, (px, py, pw, ph))
            elif itype == "line":
                p1 = (int(item["x1"] * scale_x), hud_height + int(item["y1"] * scale_y))
                p2 = (int(item["x2"] * scale_x), hud_height + int(item["y2"] * scale_y))
                line_w = max(1, int(round(min(scale_x, scale_y) * 0.35)))
                pygame.draw.line(crt_surf, col, p1, p2, line_w)
            elif itype == "circle":
                center = (int(item["x"] * scale_x), hud_height + int(item["y"] * scale_y))
                rad = max(1, int(round(item["r"] * scale_x)))
                c_w = max(1, int(round(min(scale_x, scale_y) * 0.35)))
                pygame.draw.circle(crt_surf, col, center, rad, c_w)
            elif itype == "rect":
                rx = int(item["x"] * scale_x)
                ry = hud_height + int(item["y"] * scale_y)
                rw = max(1, int(round(item["w"] * scale_x)))
                rh = max(1, int(round(item["h"] * scale_y)))
                r_w = max(1, int(round(min(scale_x, scale_y) * 0.35)))
                pygame.draw.rect(crt_surf, col, (rx, ry, rw, rh), r_w)
            elif itype == "text":
                tx = int(item["x"] * scale_x)
                ty = hud_height + int(item["y"] * scale_y)
                txt_surf = console_mgr.font.render(str(item.get("text", "")), True, col)
                crt_surf.blit(txt_surf, (tx, ty))

    @staticmethod
    def draw_led_panel(console_mgr, screen, margin_x: int, margin_top: int, screen_h: int):
        panel_y = margin_top + screen_h + 30
        led_start_x = margin_x + 350
        led_y = panel_y + 12

        if console_mgr.disk_led_timer > 0:
            console_mgr.disk_led_timer -= 1

        main_leds = [
            ("PWR", (0, 230, 60), True),
            ("DISK", (255, 50, 40), console_mgr.disk_led_timer > 0),
            ("SYNC", (240, 200, 20), True),
        ]

        curr_lx = led_start_x
        for label, color, is_on in main_leds:
            lbl_surf = console_mgr.model_font.render(label, True, (65, 60, 55))
            screen.blit(lbl_surf, (curr_lx, led_y + 16))

            pygame.draw.circle(screen, (55, 52, 48), (curr_lx + 12, led_y + 7), 8)
            pygame.draw.circle(screen, (120, 115, 105), (curr_lx + 12, led_y + 8), 7, width=1)
            led_color = color if is_on else (35, 35, 35)
            pygame.draw.circle(screen, led_color, (curr_lx + 12, led_y + 7), 5)
            if is_on:
                pygame.draw.circle(screen, (255, 255, 255), (curr_lx + 10, led_y + 5), 2)
            curr_lx += 55

        gpio_label = console_mgr.model_font.render("GPIO I/O:", True, (65, 60, 55))
        screen.blit(gpio_label, (curr_lx + 10, led_y + 16))
        curr_lx += 85

        for i in range(8):
            gpio_on = bool(console_mgr.gpio_pins[i]) if i < len(console_mgr.gpio_pins) else False
            g_color = (0, 210, 255) if gpio_on else (35, 35, 35)

            pygame.draw.circle(screen, (55, 52, 48), (curr_lx + 8, led_y + 7), 6)
            pygame.draw.circle(screen, g_color, (curr_lx + 8, led_y + 7), 4)
            if gpio_on:
                pygame.draw.circle(screen, (220, 255, 255), (curr_lx + 7, led_y + 6), 1)

            num_surf = console_mgr.gpio_num_font.render(str(i), True, (65, 60, 55))
            screen.blit(num_surf, (curr_lx + 5, led_y + 16))
            curr_lx += 22
