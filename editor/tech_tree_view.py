import pygame
from devices.display import play_retro_victory_sound, play_retro_fail_sound


class TechMapView:
    """Obsługuje widok Mapy Technologii [F2] (nawigację strzałkami, zakup poziomów oraz powrót do zadań)."""

    @staticmethod
    def get_tech_map_items(console_mgr) -> list[dict]:
        if not console_mgr.user_data:
            return []
        console_mgr._refresh_available_techs()
        unlocked = set(console_mgr.user_data.get("unlocked_techs", []))
        items = []
        for tech in console_mgr.technologies:
            if tech["id"] in unlocked:
                t_list = [t for t in console_mgr.tasks if t.get("tech_id") == tech["id"]]
                items.append({"status": "UNLOCKED", "tech": tech, "tasks": t_list})
        for idx, tech in enumerate(console_mgr.available_techs_to_pick, 1):
            items.append({"status": "AVAILABLE", "buy_index": idx, "tech": tech, "tasks": []})
        return items

    @staticmethod
    def handle_navigation_keydown(console_mgr, event) -> bool:
        items = console_mgr.get_tech_map_items()
        if items:
            console_mgr.map_cursor_idx = max(0, min(console_mgr.map_cursor_idx, len(items) - 1))
        if event.key == pygame.K_ESCAPE:
            console_mgr.current_state = console_mgr.STATE_CONSOLE
            return True
        elif event.key == pygame.K_UP and items:
            console_mgr.map_cursor_idx = max(0, console_mgr.map_cursor_idx - 1)
            console_mgr.map_task_idx = 0
            return True
        elif event.key == pygame.K_DOWN and items:
            console_mgr.map_cursor_idx = min(len(items) - 1, console_mgr.map_cursor_idx + 1)
            console_mgr.map_task_idx = 0
            return True
        elif event.key == pygame.K_LEFT and items and not console_mgr.input_text:
            cur_item = items[console_mgr.map_cursor_idx]
            t_list = cur_item.get("tasks", [])
            if t_list:
                console_mgr.map_task_idx = (console_mgr.map_task_idx - 1) % len(t_list)
            return True
        elif event.key == pygame.K_RIGHT and items and not console_mgr.input_text:
            cur_item = items[console_mgr.map_cursor_idx]
            t_list = cur_item.get("tasks", [])
            if t_list:
                console_mgr.map_task_idx = (console_mgr.map_task_idx + 1) % len(t_list)
            return True
        return False

    @staticmethod
    def handle_selection_return(console_mgr, line: str) -> None:
        items = console_mgr.get_tech_map_items()
        chosen_tech = None
        if line.isdigit():
            idx = int(line) - 1
            if 0 <= idx < len(console_mgr.available_techs_to_pick):
                chosen_tech = console_mgr.available_techs_to_pick[idx]
            else:
                console_mgr.console_lines.append("Nieprawidłowy numer! Wybierz z listy:")
                return
        elif not line and items:
            console_mgr.map_cursor_idx = max(0, min(console_mgr.map_cursor_idx, len(items) - 1))
            sel_item = items[console_mgr.map_cursor_idx]
            if sel_item["status"] == "UNLOCKED":
                t_list = sel_item.get("tasks", [])
                if t_list:
                    sel_task = t_list[console_mgr.map_task_idx % len(t_list)]
                    console_mgr.replay_task_id = sel_task["id"]
                    prev_sc = console_mgr.user_data.get("task_scores", {}).get(sel_task["id"], 0)
                    console_mgr.console_lines.append(
                        f"🔄 Wybrano zadanie z Mapy Technologii: '{sel_task['title']}' (Twój wynik: {prev_sc}/10 pkt)."
                    )
                    console_mgr.console_lines.append(
                        "   Wpisz CHECK aby poprawić ocenę na 10/10 lub wpisz DALEJ aby wrócić do nowych zadań!"
                    )
                console_mgr.current_state = console_mgr.STATE_CONSOLE
                return
            else:
                chosen_tech = sel_item["tech"]
        elif line.upper() in ("ESC", "Q", "POWROT"):
            console_mgr.current_state = console_mgr.STATE_CONSOLE
            return
        else:
            console_mgr.console_lines.append("Użyj strzałek i ENTER albo wpisz numer 1-9!")
            return

        if chosen_tech is not None:
            cost = chosen_tech.get("cost", 0)
            current_sp = console_mgr.user_data.get("science_points", 0)

            if current_sp >= cost:
                console_mgr.user_data["science_points"] -= cost
                if "unlocked_techs" not in console_mgr.user_data:
                    console_mgr.user_data["unlocked_techs"] = []
                console_mgr.user_data["unlocked_techs"].append(chosen_tech["id"])
                console_mgr.user_data["professor_hints"] = console_mgr.user_data.get("professor_hints", 1) + 1
                console_mgr.replay_task_id = None
                console_mgr.manager.save_user_state(console_mgr.user_data)
                console_mgr.disk_led_timer = 20

                play_retro_victory_sound()
                console_mgr.console_lines.append(
                    f"✅ ODBLOKOWANO: {chosen_tech['name']}! (+1 🎓 Podpowiedź Profesora, razem: {console_mgr.user_data['professor_hints']})"
                )
                _, tech_sp_earned, tech_total_sp = console_mgr.get_active_tech_info()
                console_mgr.console_lines.append(f"Punkty SP w tym rozdziale: {tech_sp_earned} / {tech_total_sp}")
                console_mgr.current_state = console_mgr.STATE_CONSOLE
            else:
                play_retro_fail_sound()
                console_mgr.console_lines.append(
                    f"❌ Za mało punktów SP! Potrzebujesz {cost} SP, a masz {current_sp} SP."
                )

    @staticmethod
    def draw(console_mgr, crt_surf, screen_w: int, screen_h: int, hud_height: int):
        items = console_mgr.get_tech_map_items()
        if items:
            console_mgr.map_cursor_idx = max(0, min(console_mgr.map_cursor_idx, len(items) - 1))

        hdr_y = hud_height + 8
        title_s = console_mgr.font.render("=== 🗺️ MAPA TECHNOLOGII I ZADAŃ (MAXOWANIE WYNIKÓW) ===", True, (255, 225, 80))
        crt_surf.blit(title_s, (20, hdr_y))
        sub_s = console_mgr.hud_font.render(
            "[↑/↓] Wybierz rozdział  |  [←/→] Wybierz zadanie do poprawy  |  [ENTER] Przejdź / Kup  |  [1-9] Szybki zakup  |  [ESC/F2] Zamknij",
            True,
            (140, 235, 165),
        )
        crt_surf.blit(sub_s, (20, hdr_y + 28))

        row_h = 28
        list_top = hdr_y + 58
        max_rows = max(1, (screen_h - list_top - 52) // row_h)
        start_i = max(0, min(console_mgr.map_cursor_idx - max_rows // 2, max(0, len(items) - max_rows)))
        end_i = min(len(items), start_i + max_rows)

        completed_set = set(console_mgr.user_data.get("completed_tasks", []))
        scores_map = console_mgr.user_data.get("task_scores", {})

        ry = list_top
        for idx in range(start_i, end_i):
            item = items[idx]
            is_sel = idx == console_mgr.map_cursor_idx
            tech = item["tech"]
            if is_sel:
                pygame.draw.rect(crt_surf, (22, 62, 32), (14, ry - 2, screen_w - 28, row_h))
                pygame.draw.rect(crt_surf, (90, 240, 120), (14, ry - 2, screen_w - 28, row_h), width=1)

            prefix = "▸ " if is_sel else "  "
            if item["status"] == "UNLOCKED":
                t_list = item.get("tasks", [])
                done_cnt = sum(1 for t in t_list if t["id"] in completed_set)
                row_txt = f"{prefix}✅ {tech['name']} (Zadania: {done_cnt}/{len(t_list)})"
                if is_sel and t_list:
                    sel_t = t_list[console_mgr.map_task_idx % len(t_list)]
                    sc = scores_map.get(sel_t["id"], 0)
                    row_txt += f"  ◄ Zad.{console_mgr.map_task_idx % len(t_list) + 1}: {sel_t['title'][:26]} [{sc}/10⭐] ►"
                col = (120, 255, 150) if is_sel else (150, 220, 160)
            else:
                b_idx = item.get("buy_index", 1)
                cost = tech.get("cost", 10)
                can_buy = console_mgr.user_data.get("science_points", 0) >= cost
                row_txt = f"{prefix}🔓 [{b_idx}] DO ODBLOKOWANIA: {tech['name']} (Koszt: {cost} SP)"
                col = (255, 230, 90) if can_buy else (255, 110, 110)

            crt_surf.blit(console_mgr.hud_font.render(row_txt, True, col), (20, ry + 3))
            ry += row_h
