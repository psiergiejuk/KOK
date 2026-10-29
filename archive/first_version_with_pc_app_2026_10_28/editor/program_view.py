import pygame


class ProgramEditorView:
    """Obsługuje pełnoekranowy edytor kodu KOK-EDIT (klawiatura + renderowanie)."""

    @staticmethod
    def handle_keydown(console_mgr, event) -> bool:
        mods = getattr(event, "mod", 0)
        is_ctrl = bool(mods & pygame.KMOD_CTRL)
        plines = console_mgr.command_registry.program_lines
        if not plines:
            plines.append("")
        console_mgr.editor_row = max(0, min(console_mgr.editor_row, len(plines) - 1))
        console_mgr.editor_col = max(0, min(console_mgr.editor_col, len(plines[console_mgr.editor_row])))

        # [Ctrl+S] Zapisz program
        if is_ctrl and event.key == pygame.K_s:
            prog_name = getattr(console_mgr.command_registry, "current_program_name", "PROGRAM") or "PROGRAM"
            console_mgr.command_registry.saved_programs[prog_name] = list(plines)
            if console_mgr.user_data is not None:
                console_mgr.user_data["program_lines"] = list(plines)
                console_mgr.user_data["saved_programs"] = dict(console_mgr.command_registry.saved_programs)
                console_mgr.user_data.setdefault("action_counts", {})["SAVE"] = (
                    console_mgr.user_data.get("action_counts", {}).get("SAVE", 0) + 1
                )
                console_mgr.manager.save_user_state(console_mgr.user_data)
            console_mgr.disk_led_timer = 20
            console_mgr.editor_status_msg = f"💾 Zapisano {prog_name}.BAS! (Naciśnij ESC aby zamknąć edytor)"
            console_mgr._complete_active_task_if_valid("SAVE")
            return True

        # [ESC] lub [Ctrl+Q] Zamknij edytor (CLOSE)
        if event.key == pygame.K_ESCAPE or (is_ctrl and event.key == pygame.K_q):
            if console_mgr.user_data is not None:
                console_mgr.user_data["program_lines"] = list(plines)
                console_mgr.user_data["saved_programs"] = dict(console_mgr.command_registry.saved_programs)
                console_mgr.manager.save_user_state(console_mgr.user_data)
            console_mgr.disk_led_timer = 15
            console_mgr.current_state = console_mgr.STATE_CONSOLE
            console_mgr.console_lines.append(
                "📝 Zamknięto edytor KOK-EDIT. Wpisz RUN aby uruchomić program lub LIST aby zobaczyć kod."
            )
            console_mgr.check_tech_completion()
            return True

        if event.key == pygame.K_UP:
            if console_mgr.editor_row > 0:
                console_mgr.editor_row -= 1
                console_mgr.editor_col = min(console_mgr.editor_col, len(plines[console_mgr.editor_row]))
        elif event.key == pygame.K_DOWN:
            if console_mgr.editor_row < len(plines) - 1:
                console_mgr.editor_row += 1
                console_mgr.editor_col = min(console_mgr.editor_col, len(plines[console_mgr.editor_row]))
        elif event.key == pygame.K_LEFT:
            if console_mgr.editor_col > 0:
                console_mgr.editor_col -= 1
            elif console_mgr.editor_row > 0:
                console_mgr.editor_row -= 1
                console_mgr.editor_col = len(plines[console_mgr.editor_row])
        elif event.key == pygame.K_RIGHT:
            if console_mgr.editor_col < len(plines[console_mgr.editor_row]):
                console_mgr.editor_col += 1
            elif console_mgr.editor_row < len(plines) - 1:
                console_mgr.editor_row += 1
                console_mgr.editor_col = 0
        elif event.key == pygame.K_BACKSPACE:
            cur_line = plines[console_mgr.editor_row]
            if console_mgr.editor_col > 0:
                plines[console_mgr.editor_row] = (
                    cur_line[: console_mgr.editor_col - 1] + cur_line[console_mgr.editor_col :]
                )
                console_mgr.editor_col -= 1
            elif console_mgr.editor_row > 0:
                prev_len = len(plines[console_mgr.editor_row - 1])
                plines[console_mgr.editor_row - 1] += cur_line
                plines.pop(console_mgr.editor_row)
                console_mgr.editor_row -= 1
                console_mgr.editor_col = prev_len
        elif event.key == pygame.K_DELETE:
            cur_line = plines[console_mgr.editor_row]
            if console_mgr.editor_col < len(cur_line):
                plines[console_mgr.editor_row] = (
                    cur_line[: console_mgr.editor_col] + cur_line[console_mgr.editor_col + 1 :]
                )
            elif console_mgr.editor_row < len(plines) - 1:
                plines[console_mgr.editor_row] += plines.pop(console_mgr.editor_row + 1)
        elif event.key == pygame.K_RETURN:
            cur_line = plines[console_mgr.editor_row]
            left_part = cur_line[: console_mgr.editor_col]
            right_part = cur_line[console_mgr.editor_col :]
            plines[console_mgr.editor_row] = left_part
            plines.insert(console_mgr.editor_row + 1, right_part)
            console_mgr.editor_row += 1
            console_mgr.editor_col = 0
        else:
            if hasattr(event, "unicode") and event.unicode and event.unicode.isprintable() and not is_ctrl:
                cur_line = plines[console_mgr.editor_row]
                plines[console_mgr.editor_row] = (
                    cur_line[: console_mgr.editor_col] + event.unicode + cur_line[console_mgr.editor_col :]
                )
                console_mgr.editor_col += len(event.unicode)
        return True

    @staticmethod
    def draw(console_mgr, crt_surf, screen_w: int, screen_h: int, hud_height: int):
        prog_name = getattr(console_mgr.command_registry, "current_program_name", "PROGRAM")
        plines = console_mgr.command_registry.program_lines or [""]
        header_y = hud_height + 4
        pygame.draw.rect(crt_surf, (16, 42, 24), (0, hud_height, screen_w, 28))
        pygame.draw.line(crt_surf, (60, 160, 80), (0, hud_height + 28), (screen_w, hud_height + 28), 1)
        hdr_txt = f"📝 KOK-EDIT: {prog_name}.BAS  |  Wiersz: {console_mgr.editor_row + 1}/{len(plines)}  Kol: {console_mgr.editor_col + 1}"
        crt_surf.blit(console_mgr.hud_font.render(hdr_txt, True, (180, 255, 180)), (16, header_y + 4))

        line_h = 24
        code_top = hud_height + 36
        code_bottom = screen_h - 42
        max_vis = max(1, (code_bottom - code_top) // line_h)
        start_idx = max(0, min(console_mgr.editor_row - max_vis // 2, max(0, len(plines) - max_vis)))
        end_idx = min(len(plines), start_idx + max_vis)

        y_cur = code_top
        for idx in range(start_idx, end_idx):
            is_curr_row = idx == console_mgr.editor_row
            if is_curr_row:
                pygame.draw.rect(crt_surf, (18, 48, 24), (10, y_cur - 1, screen_w - 20, line_h))

            num_str = f"{idx + 1:3d} │ "
            num_surf = console_mgr.font.render(num_str, True, (90, 200, 110) if is_curr_row else (65, 135, 80))
            crt_surf.blit(num_surf, (16, y_cur))
            code_x = 16 + num_surf.get_width()

            line_str = plines[idx]
            if is_curr_row:
                left_s = line_str[: console_mgr.editor_col]
                right_s = line_str[console_mgr.editor_col :]
                if left_s:
                    ls = console_mgr.font.render(left_s, True, (200, 255, 200))
                    crt_surf.blit(ls, (code_x, y_cur))
                    code_x += ls.get_width()
                cur_s = console_mgr.font.render("█", True, (100, 255, 140))
                crt_surf.blit(cur_s, (code_x, y_cur))
                code_x += cur_s.get_width()
                if right_s:
                    rs = console_mgr.font.render(right_s, True, (200, 255, 200))
                    crt_surf.blit(rs, (code_x, y_cur))
            else:
                cs = console_mgr.font.render(line_str, True, (150, 245, 150))
                crt_surf.blit(cs, (code_x, y_cur))
            y_cur += line_h

        footer_y = screen_h - 36
        pygame.draw.rect(crt_surf, (16, 42, 24), (0, footer_y, screen_w, 36))
        pygame.draw.line(crt_surf, (60, 160, 80), (0, footer_y), (screen_w, footer_y), 1)
        shortcuts_txt = "[Ctrl+S] Zapisz (SAVE)   │   [ESC / Ctrl+Q] Zamknij edytor (CLOSE)"
        if console_mgr.editor_status_msg:
            shortcuts_txt += f"   │   {console_mgr.editor_status_msg}"
        crt_surf.blit(console_mgr.hud_font.render(shortcuts_txt, True, (120, 255, 160)), (16, footer_y + 9))
