import hashlib
import json
import os
import sqlite3


class UserManager:
    """Zarządza rejestracją, logowaniem oraz stanem i zapisem profilu użytkownika w bazie SQLite."""

    def __init__(self, data_dir: str = "data/users", db_path: str = None):
        self._data_dir = data_dir
        if db_path is not None:
            self.db_path = db_path
        elif data_dir.endswith(".sqlite") or data_dir.endswith(".db"):
            self.db_path = data_dir
        else:
            base_parent = os.path.dirname(data_dir) or "data"
            self.db_path = os.path.join(base_parent, "kok_users.sqlite")

        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        os.makedirs(self._data_dir, exist_ok=True)

        self._init_db()
        self._auto_migrate_json_files()

    @property
    def users_dir(self) -> str:
        return self.data_dir

    @users_dir.setter
    def users_dir(self, value: str):
        self.data_dir = value

    @property
    def data_dir(self) -> str:
        return self._data_dir

    @data_dir.setter
    def data_dir(self, value: str):
        self._data_dir = value
        if value:
            if value.endswith(".sqlite") or value.endswith(".db"):
                self.db_path = value
            else:
                base_parent = os.path.dirname(value) or "data"
                self.db_path = os.path.join(base_parent, "kok_users.sqlite")
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
            os.makedirs(self._data_dir, exist_ok=True)
            self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _init_db(self):
        """Tworzy tabele użytkowników, klas oraz powiązań z obsługą ról i licencji."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    first_name TEXT NOT NULL,
                    last_name TEXT DEFAULT '',
                    age INTEGER DEFAULT 10,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'student',
                    owner_teacher TEXT DEFAULT NULL,
                    max_students INTEGER DEFAULT 50,
                    license_type TEXT DEFAULT 'school_yearly',
                    license_expires_at TIMESTAMP DEFAULT NULL,
                    is_active INTEGER DEFAULT 1,
                    recent_commands TEXT DEFAULT '[]',
                    science_points INTEGER DEFAULT 0,
                    professor_hints INTEGER DEFAULT 1,
                    unlocked_techs TEXT DEFAULT '["HELP_1"]',
                    completed_tasks TEXT DEFAULT '[]',
                    completed_quizzes TEXT DEFAULT '[]',
                    task_scores TEXT DEFAULT '{}',
                    task_submissions TEXT DEFAULT '{}',
                    action_counts TEXT DEFAULT '{}',
                    variables TEXT DEFAULT '{}',
                    data_json TEXT DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS classes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    owner_teacher TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS class_members (
                    class_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (class_id, username),
                    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
                );
            """)

            # Migracje kolumn dla istniejących baz
            cols = [r["name"] for r in conn.execute("PRAGMA table_info(users);").fetchall()]
            new_cols = {
                "role": "TEXT DEFAULT 'student'",
                "owner_teacher": "TEXT DEFAULT NULL",
                "max_students": "INTEGER DEFAULT 50",
                "license_type": "TEXT DEFAULT 'school_yearly'",
                "license_expires_at": "TIMESTAMP DEFAULT NULL",
                "is_active": "INTEGER DEFAULT 1",
                "recent_commands": "TEXT DEFAULT '[]'"
            }
            for col_name, col_def in new_cols.items():
                if col_name not in cols:
                    try:
                        conn.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_def};")
                    except Exception:
                        pass

            # Upewnij się, że użytkownik admin ma uprawnienia administratora
            admin_row = conn.execute("SELECT 1 FROM users WHERE LOWER(username) = 'admin'").fetchone()
            if admin_row:
                conn.execute("UPDATE users SET role = 'admin' WHERE LOWER(username) = 'admin';")
            else:
                admin_pass_hash = self._hash_password("admin")
                conn.execute("""
                    INSERT INTO users (username, first_name, last_name, age, password_hash, role)
                    VALUES ('admin', 'Administrator', 'Systemu', 40, ?, 'admin');
                """, (admin_pass_hash,))
            conn.commit()

    def _auto_migrate_json_files(self):
        """Automatycznie importuje istniejące profile JSON z dysku do bazy SQLite."""
        if not os.path.exists(self.data_dir):
            return
        try:
            for fname in os.listdir(self.data_dir):
                if fname.endswith(".json"):
                    fpath = os.path.join(self.data_dir, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            u_data = json.load(f)
                            if isinstance(u_data, dict) and u_data.get("username"):
                                uname = u_data["username"]
                                if not self.user_exists(uname):
                                    self.save_user_state(u_data)
                    except Exception:
                        pass
        except Exception:
            pass

    def _hash_password(self, password: str) -> str:
        """Haszowanie hasła algorytmem SHA-256."""
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def _row_to_user_data(self, row: sqlite3.Row) -> dict:
        """Konwertuje wiersz bazy SQLite do kompletnego słownika gracza."""
        data = {}
        if row["data_json"]:
            try:
                data = json.loads(row["data_json"])
            except Exception:
                data = {}

        data["username"] = row["username"]
        data["first_name"] = row["first_name"]
        data["last_name"] = row["last_name"]
        data["age"] = row["age"]
        data["password_hash"] = row["password_hash"]
        data["role"] = row["role"] if ("role" in row.keys() and row["role"]) else data.get("role", "student")
        data["owner_teacher"] = row["owner_teacher"] if ("owner_teacher" in row.keys()) else data.get("owner_teacher")
        data["max_students"] = row["max_students"] if ("max_students" in row.keys() and row["max_students"] is not None) else data.get("max_students", 50)
        data["license_type"] = row["license_type"] if ("license_type" in row.keys() and row["license_type"]) else data.get("license_type", "school_yearly")
        data["license_expires_at"] = str(row["license_expires_at"]) if ("license_expires_at" in row.keys() and row["license_expires_at"]) else data.get("license_expires_at")
        data["is_active"] = int(row["is_active"]) if ("is_active" in row.keys() and row["is_active"] is not None) else data.get("is_active", 1)
        data["science_points"] = row["science_points"]
        data["professor_hints"] = row["professor_hints"]

        def parse_json(field_name, default):
            val = row[field_name]
            if val is not None:
                try:
                    return json.loads(val)
                except Exception:
                    return default
            return data.get(field_name, default)

        data["unlocked_techs"] = parse_json("unlocked_techs", ["HELP_1"])
        data["completed_tasks"] = parse_json("completed_tasks", [])
        data["completed_quizzes"] = parse_json("completed_quizzes", [])
        data["task_scores"] = parse_json("task_scores", {})
        data["task_submissions"] = parse_json("task_submissions", {})
        data["action_counts"] = parse_json("action_counts", {})
        data["variables"] = parse_json("variables", {})
        data["recent_commands"] = parse_json("recent_commands", [])
        return data

    def user_exists(self, username: str) -> bool:
        """Sprawdza, czy profil użytkownika o podanym loginie istnieje w bazie."""
        safe_name = username.strip().lower()
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM users WHERE LOWER(username) = ?", (safe_name,)
            ).fetchone()
            return row is not None

    def get_user_filepath(self, username: str) -> str:
        """Zachowane dla kompatybilności wstecznej."""
        return os.path.join(self.data_dir, f"{username.strip().lower()}.json")

    def register_user(
        self, username: str, first_name: str, last_name: str, age: int, password: str,
        role: str = "student", owner_teacher: str = None
    ) -> dict:
        """Tworzy nowy profil użytkownika i zapisuje go w bazie SQLite."""
        valid_role = role.lower().strip() if role else "student"
        if valid_role not in ("student", "teacher", "admin"):
            valid_role = "student"

        user_data = {
            "username": username.strip(),
            "first_name": first_name.strip(),
            "last_name": last_name.strip(),
            "age": int(age),
            "password_hash": self._hash_password(password),
            "role": valid_role,
            "owner_teacher": owner_teacher.strip() if owner_teacher else None,
            "max_students": 50 if valid_role == "teacher" else 0,
            "license_type": "school_yearly",
            "is_active": 1,
            "recent_commands": [],
            "science_points": 0,
            "professor_hints": 1,
            "unlocked_techs": ["HELP_1"],
            "completed_tasks": [],
            "task_scores": {},
            "task_submissions": {},
            "action_counts": {},
            "variables": {}
        }
        self.save_user_state(user_data)
        return user_data

    def authenticate_user(self, username: str, password: str) -> dict | None:
        """Weryfikuje hasło i wczytuje dane użytkownika z bazy SQLite."""
        safe_name = username.strip().lower()
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE LOWER(username) = ?", (safe_name,)
            ).fetchone()
            if not row:
                return None
            user_data = self._row_to_user_data(row)
            if user_data.get("password_hash") == self._hash_password(password):
                return user_data
            return None

    def save_user_state(self, user_data: dict):
        """Zapisuje aktualny stan profilu gracza w bazie SQLite."""
        username = user_data.get("username", "").strip()
        if not username:
            return

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO users (
                    username, first_name, last_name, age, password_hash, role,
                    owner_teacher, max_students, license_type, license_expires_at, is_active, recent_commands,
                    science_points, professor_hints, unlocked_techs, completed_tasks,
                    completed_quizzes, task_scores, task_submissions, action_counts,
                    variables, data_json, updated_at
                ) VALUES (
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?, CURRENT_TIMESTAMP
                )
                ON CONFLICT(username) DO UPDATE SET
                    first_name=excluded.first_name,
                    last_name=excluded.last_name,
                    age=excluded.age,
                    password_hash=COALESCE(NULLIF(excluded.password_hash, ''), users.password_hash),
                    role=COALESCE(NULLIF(excluded.role, ''), users.role, 'student'),
                    owner_teacher=COALESCE(excluded.owner_teacher, users.owner_teacher),
                    max_students=COALESCE(excluded.max_students, users.max_students),
                    license_type=COALESCE(excluded.license_type, users.license_type),
                    license_expires_at=COALESCE(excluded.license_expires_at, users.license_expires_at),
                    is_active=COALESCE(excluded.is_active, users.is_active),
                    recent_commands=COALESCE(excluded.recent_commands, users.recent_commands),
                    science_points=excluded.science_points,
                    professor_hints=excluded.professor_hints,
                    unlocked_techs=excluded.unlocked_techs,
                    completed_tasks=excluded.completed_tasks,
                    completed_quizzes=excluded.completed_quizzes,
                    task_scores=excluded.task_scores,
                    task_submissions=excluded.task_submissions,
                    action_counts=excluded.action_counts,
                    variables=excluded.variables,
                    data_json=excluded.data_json,
                    updated_at=CURRENT_TIMESTAMP
            """, (
                username,
                user_data.get("first_name", username),
                user_data.get("last_name", ""),
                int(user_data.get("age", 10)),
                user_data.get("password_hash", ""),
                user_data.get("role", "student"),
                user_data.get("owner_teacher"),
                int(user_data.get("max_students", 50 if user_data.get("role") == "teacher" else 0)),
                user_data.get("license_type", "school_yearly"),
                user_data.get("license_expires_at"),
                int(user_data.get("is_active", 1)),
                json.dumps(user_data.get("recent_commands", []), ensure_ascii=False),
                int(user_data.get("science_points", 0)),
                int(user_data.get("professor_hints", 1)),
                json.dumps(user_data.get("unlocked_techs", ["HELP_1"]), ensure_ascii=False),
                json.dumps(user_data.get("completed_tasks", []), ensure_ascii=False),
                json.dumps(user_data.get("completed_quizzes", []), ensure_ascii=False),
                json.dumps(user_data.get("task_scores", {}), ensure_ascii=False),
                json.dumps(user_data.get("task_submissions", {}), ensure_ascii=False),
                json.dumps(user_data.get("action_counts", {}), ensure_ascii=False),
                json.dumps(user_data.get("variables", {}), ensure_ascii=False),
                json.dumps(user_data, ensure_ascii=False)
            ))

    def delete_user(self, username: str):
        """Usuwa profil użytkownika z bazy SQLite oraz z powiązań klasowych."""
        safe_name = username.strip().lower()
        with self._get_connection() as conn:
            conn.execute("DELETE FROM class_members WHERE LOWER(username) = ?", (safe_name,))
            conn.execute("DELETE FROM users WHERE LOWER(username) = ?", (safe_name,))

        filepath = self.get_user_filepath(username)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception:
                pass

    def get_all_users(self) -> list[dict]:
        """Zwraca listę wszystkich zarejestrowanych profili."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM users ORDER BY username ASC").fetchall()
            return [self._row_to_user_data(r) for r in rows]

    # =========================================================================
    # KONTROLA AUTORYZACJI I WAŻNOŚCI LICENCJI
    # =========================================================================

    def is_user_authorized_to_login(self, username: str) -> tuple[bool, str]:
        """Sprawdza czy konto jest aktywne oraz czy licencja nauczyciela nie wygasła."""
        safe_name = username.strip().lower()
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE LOWER(username) = ?", (safe_name,)).fetchone()
            if not row:
                return False, f"Użytkownik '{username}' nie istnieje."
            u = self._row_to_user_data(row)
            if not u.get("is_active", 1):
                return False, "Konto jest zablokowane. Skontaktuj się z administratorem."

            # Jeśli rola to nauczyciel, sprawdzamy ważność jego subskrypcji
            if u.get("role") == "teacher":
                exp = u.get("license_expires_at")
                if exp:
                    from datetime import datetime
                    try:
                        exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00").split()[0])
                        if datetime.now() > exp_dt:
                            return False, f"Twoja subskrypcja nauczycielska wygasła ({exp[:10]}). Przedłuż licencję, aby się zalogować."
                    except Exception:
                        pass

            # Jeśli uczeń jest przypisany do nauczyciela, sprawdzamy status nauczyciela
            teacher_name = u.get("owner_teacher")
            if teacher_name and u.get("role") == "student":
                t_row = conn.execute("SELECT * FROM users WHERE LOWER(username) = ?", (teacher_name.lower(),)).fetchone()
                if t_row:
                    t_data = self._row_to_user_data(t_row)
                    if not t_data.get("is_active", 1):
                        return False, f"Konto Twojego nauczyciela ({teacher_name}) jest nieaktywne."
                    # Sprawdzenie daty ważności subskrypcji nauczyciela
                    exp = t_data.get("license_expires_at")
                    if exp:
                        from datetime import datetime
                        try:
                            exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00").split()[0])
                            if datetime.now() > exp_dt:
                                return False, f"Subskrypcja szkolna Twojego nauczyciela ({teacher_name}) wygasła ({exp[:10]})."
                        except Exception:
                            pass
            return True, ""

    def record_user_command(self, username: str, command_line: str):
        """Zapisuje ostatnią komendę do historii użytkownika (max 50 ostatnich)."""
        safe_name = username.strip().lower()
        cmd = command_line.strip()
        if not cmd:
            return
        with self._get_connection() as conn:
            row = conn.execute("SELECT recent_commands FROM users WHERE LOWER(username) = ?", (safe_name,)).fetchone()
            if not row:
                return
            cmds = json.loads(row["recent_commands"]) if row["recent_commands"] else []
            from datetime import datetime
            cmds.append(f"[{datetime.now().strftime('%H:%M:%S')}] {cmd}")
            if len(cmds) > 50:
                cmds = cmds[-50:]
            conn.execute("UPDATE users SET recent_commands = ? WHERE LOWER(username) = ?", (json.dumps(cmds, ensure_ascii=False), safe_name))
            conn.commit()

    def get_user_recent_commands(self, username: str, limit: int = 20) -> list[str]:
        """Pobiera listę ostatnich komend wpisanych przez użytkownika."""
        safe_name = username.strip().lower()
        with self._get_connection() as conn:
            row = conn.execute("SELECT recent_commands FROM users WHERE LOWER(username) = ?", (safe_name,)).fetchone()
            if not row or not row["recent_commands"]:
                return []
            cmds = json.loads(row["recent_commands"])
            return cmds[-limit:]

    # =========================================================================
    # ZDALNE ZARZĄDZANIE TECHNOLOGIAMI (ADMIN TECH)
    # =========================================================================

    def set_user_tech(self, username: str, tech_id: str, add: bool = True) -> tuple[bool, str, list[str]]:
        """Zdalnie odblokowuje lub blokuje technologię dla danego użytkownika."""
        safe_name = username.strip().lower()
        t_id = tech_id.strip().upper()
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE LOWER(username) = ?", (safe_name,)).fetchone()
            if not row:
                return False, f"Użytkownik '{username}' nie istnieje.", []
            u = self._row_to_user_data(row)
            techs = set(u.get("unlocked_techs", ["HELP_1"]))
            if add:
                techs.add(t_id)
                msg = f"Odblokowano technologię {t_id} dla '{username}'."
            else:
                if t_id == "HELP_1":
                    return False, "Nie można odebrać bazowej technologii HELP_1.", list(techs)
                techs.discard(t_id)
                msg = f"Zablokowano technologię {t_id} dla '{username}'."

            tech_list = sorted(list(techs))
            u["unlocked_techs"] = tech_list
            conn.execute("UPDATE users SET unlocked_techs = ?, data_json = ?, updated_at = CURRENT_TIMESTAMP WHERE LOWER(username) = ?",
                         (json.dumps(tech_list, ensure_ascii=False), json.dumps(u, ensure_ascii=False), safe_name))
            conn.commit()
            return True, msg, tech_list

    def reset_user_tech(self, username: str) -> tuple[bool, str]:
        """Resetuje technologie gracza do stanu początkowego (HELP_1)."""
        safe_name = username.strip().lower()
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE LOWER(username) = ?", (safe_name,)).fetchone()
            if not row:
                return False, f"Użytkownik '{username}' nie istnieje."
            u = self._row_to_user_data(row)
            u["unlocked_techs"] = ["HELP_1"]
            conn.execute("UPDATE users SET unlocked_techs = '[\"HELP_1\"]', data_json = ?, updated_at = CURRENT_TIMESTAMP WHERE LOWER(username) = ?",
                         (json.dumps(u, ensure_ascii=False), safe_name))
            conn.commit()
            return True, f"Zresetowano technologie użytkownika '{username}' do [HELP_1]."

    def unlock_all_user_tech(self, username: str, all_tech_ids: list[str]) -> tuple[bool, str]:
        """Odblokowuje wszystkie technologie dla użytkownika."""
        safe_name = username.strip().lower()
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE LOWER(username) = ?", (safe_name,)).fetchone()
            if not row:
                return False, f"Użytkownik '{username}' nie istnieje."
            u = self._row_to_user_data(row)
            u["unlocked_techs"] = list(all_tech_ids)
            conn.execute("UPDATE users SET unlocked_techs = ?, data_json = ?, updated_at = CURRENT_TIMESTAMP WHERE LOWER(username) = ?",
                         (json.dumps(all_tech_ids, ensure_ascii=False), json.dumps(u, ensure_ascii=False), safe_name))
            conn.commit()
            return True, f"Odblokowano wszystkie technologie ({len(all_tech_ids)}) dla '{username}'."

    def set_class_tech(self, class_code: str, tech_id: str, add: bool = True) -> tuple[bool, str]:
        """Zdalnie nadaje lub odbiera technologię wszystkim uczniom w danej klasie."""
        students = self.get_class_students(class_code)
        if not students:
            return False, f"Klasa '{class_code}' nie istnieje lub nie ma w niej uczniów."
        for s in students:
            self.set_user_tech(s["username"], tech_id, add=add)
        act = "Odblokowano" if add else "Zablokowano"
        return True, f"{act} technologię {tech_id.upper()} dla całej klasy '{class_code}' ({len(students)} uczniów)."

    # =========================================================================
    # ZARZĄDZANIE KLASAMI I GRUPAMI (LINUX STYLE GROUPS)
    # =========================================================================

    def create_class(self, code: str, name: str, owner_teacher: str, description: str = "") -> tuple[bool, str, dict | None]:
        """Tworzy nową klasę / grupę przypisaną do nauczyciela."""
        c_code = code.strip().upper()
        if not c_code or not name:
            return False, "Kod i nazwa klasy są wymagane.", None
        with self._get_connection() as conn:
            existing = conn.execute("SELECT 1 FROM classes WHERE code = ?", (c_code,)).fetchone()
            if existing:
                return False, f"Klasa o kodzie '{c_code}' już istnieje.", None
            cur = conn.execute("""
                INSERT INTO classes (code, name, owner_teacher, description)
                VALUES (?, ?, ?, ?);
            """, (c_code, name.strip(), owner_teacher.strip(), description.strip()))
            conn.commit()
            return True, f"Utworzono klasę [{c_code}] - {name}.", {
                "id": cur.lastrowid, "code": c_code, "name": name, "owner_teacher": owner_teacher
            }

    def delete_class(self, code: str, owner_teacher: str = None) -> tuple[bool, str]:
        """Usuwa klasę (odpina uczniów, nie usuwa ich kont)."""
        c_code = code.strip().upper()
        with self._get_connection() as conn:
            cls_row = conn.execute("SELECT * FROM classes WHERE code = ?", (c_code,)).fetchone()
            if not cls_row:
                return False, f"Klasa '{c_code}' nie istnieje."
            if owner_teacher and cls_row["owner_teacher"].lower() != owner_teacher.lower():
                return False, "Brak uprawnień: możesz usuwać tylko własne klasy."
            conn.execute("DELETE FROM class_members WHERE class_id = ?", (cls_row["id"],))
            conn.execute("DELETE FROM classes WHERE id = ?", (cls_row["id"],))
            conn.commit()
            return True, f"Usunięto klasę [{c_code}]."

    def list_classes(self, owner_teacher: str = None) -> list[dict]:
        """Zwraca listę klas wraz z liczbą uczniów i średnią punktów SP."""
        with self._get_connection() as conn:
            if owner_teacher:
                classes = conn.execute("SELECT * FROM classes WHERE LOWER(owner_teacher) = ? ORDER BY code ASC",
                                       (owner_teacher.strip().lower(),)).fetchall()
            else:
                classes = conn.execute("SELECT * FROM classes ORDER BY code ASC").fetchall()

            res = []
            for c in classes:
                cid = c["id"]
                members = conn.execute("""
                    SELECT u.science_points, u.completed_tasks
                    FROM class_members m
                    JOIN users u ON LOWER(m.username) = LOWER(u.username)
                    WHERE m.class_id = ?
                """, (cid,)).fetchall()
                cnt = len(members)
                total_sp = sum(m["science_points"] for m in members) if cnt > 0 else 0
                avg_sp = round(total_sp / cnt, 1) if cnt > 0 else 0.0
                res.append({
                    "id": cid,
                    "code": c["code"],
                    "name": c["name"],
                    "owner_teacher": c["owner_teacher"],
                    "description": c["description"] or "",
                    "students_count": cnt,
                    "avg_sp": avg_sp,
                    "created_at": str(c["created_at"])[:16] if c["created_at"] else ""
                })
            return res

    def get_class(self, code: str) -> dict | None:
        """Pobiera dane klasy po kodzie."""
        c_code = code.strip().upper()
        with self._get_connection() as conn:
            r = conn.execute("SELECT * FROM classes WHERE code = ?", (c_code,)).fetchone()
            if not r:
                return None
            return dict(r)

    def add_student_to_class(self, class_code: str, username: str, owner_teacher: str = None) -> tuple[bool, str]:
        """Dodaje ucznia do klasy (wielokrotna przynależność w stylu grup Linux)."""
        c_code = class_code.strip().upper()
        safe_user = username.strip().lower()
        with self._get_connection() as conn:
            cls_row = conn.execute("SELECT * FROM classes WHERE code = ?", (c_code,)).fetchone()
            if not cls_row:
                return False, f"Klasa '{c_code}' nie istnieje."
            if owner_teacher and cls_row["owner_teacher"].lower() != owner_teacher.lower():
                return False, "Możesz dodawać uczniów tylko do własnych klas."
            user_row = conn.execute("SELECT 1 FROM users WHERE LOWER(username) = ?", (safe_user,)).fetchone()
            if not user_row:
                return False, f"Użytkownik '{username}' nie istnieje."

            # Sprawdź czy już należy
            already = conn.execute("SELECT 1 FROM class_members WHERE class_id = ? AND LOWER(username) = ?",
                                   (cls_row["id"], safe_user)).fetchone()
            if already:
                return False, f"Uczeń '{username}' już jest w klasie [{c_code}]."

            conn.execute("INSERT INTO class_members (class_id, username) VALUES (?, ?)", (cls_row["id"], safe_user))
            # Jeśli uczeń nie miał przypisanego nauczyciela, przypisz nauczyciela tej klasy
            conn.execute("UPDATE users SET owner_teacher = ? WHERE LOWER(username) = ? AND owner_teacher IS NULL",
                         (cls_row["owner_teacher"], safe_user))
            conn.commit()
            return True, f"Dodano ucznia '{username}' do klasy [{c_code}]."

    def remove_student_from_class(self, class_code: str, username: str, owner_teacher: str = None) -> tuple[bool, str]:
        """Wypisuje ucznia z klasy."""
        c_code = class_code.strip().upper()
        safe_user = username.strip().lower()
        with self._get_connection() as conn:
            cls_row = conn.execute("SELECT * FROM classes WHERE code = ?", (c_code,)).fetchone()
            if not cls_row:
                return False, f"Klasa '{c_code}' nie istnieje."
            if owner_teacher and cls_row["owner_teacher"].lower() != owner_teacher.lower():
                return False, "Możesz wypisywać uczniów tylko z własnych klas."
            conn.execute("DELETE FROM class_members WHERE class_id = ? AND LOWER(username) = ?",
                         (cls_row["id"], safe_user))
            conn.commit()
            return True, f"Wypisano ucznia '{username}' z klasy [{c_code}]."

    def get_class_students(self, class_code: str) -> list[dict]:
        """Zwraca listę uczniów należących do danej klasy."""
        c_code = class_code.strip().upper()
        with self._get_connection() as conn:
            cls_row = conn.execute("SELECT id FROM classes WHERE code = ?", (c_code,)).fetchone()
            if not cls_row:
                return []
            rows = conn.execute("""
                SELECT u.username, u.first_name, u.last_name, u.age, u.science_points,
                       u.professor_hints, u.completed_tasks, u.completed_quizzes, u.unlocked_techs,
                       m.joined_at
                FROM class_members m
                JOIN users u ON LOWER(m.username) = LOWER(u.username)
                WHERE m.class_id = ?
                ORDER BY u.science_points DESC, u.username ASC
            """, (cls_row["id"],)).fetchall()
            res = []
            for r in rows:
                c_tasks = json.loads(r["completed_tasks"]) if r["completed_tasks"] else []
                c_quizzes = json.loads(r["completed_quizzes"]) if r["completed_quizzes"] else []
                res.append({
                    "username": r["username"],
                    "first_name": r["first_name"],
                    "last_name": r["last_name"],
                    "age": r["age"],
                    "science_points": r["science_points"],
                    "professor_hints": r["professor_hints"],
                    "tasks_count": len(c_tasks),
                    "quizzes_count": len(c_quizzes),
                    "unlocked_techs": json.loads(r["unlocked_techs"]) if r["unlocked_techs"] else [],
                    "joined_at": str(r["joined_at"])[:16] if r["joined_at"] else ""
                })
            return res

    def get_student_classes(self, username: str) -> list[str]:
        """Zwraca kody klas, do których należy uczeń."""
        safe_user = username.strip().lower()
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT c.code FROM classes c
                JOIN class_members m ON c.id = m.class_id
                WHERE LOWER(m.username) = ?
                ORDER BY c.code ASC
            """, (safe_user,)).fetchall()
            return [r["code"] for r in rows]

    def get_class_report(self, class_code: str) -> dict | None:
        """Generuje zbiorczy raport statystyczny i ranking dla klasy."""
        c_code = class_code.strip().upper()
        cls_info = self.get_class(c_code)
        if not cls_info:
            return None

        students = self.get_class_students(c_code)
        cnt = len(students)
        if cnt == 0:
            return {
                "class_code": c_code,
                "class_name": cls_info["name"],
                "owner_teacher": cls_info["owner_teacher"],
                "students_count": 0,
                "avg_sp": 0.0,
                "ranking": [],
                "recent_stuck_students": []
            }

        total_sp = sum(s["science_points"] for s in students)
        avg_sp = round(total_sp / cnt, 1)

        # Sprawdzenie kto ma ostatnie błędy w recent_commands
        stuck = []
        with self._get_connection() as conn:
            for s in students:
                row = conn.execute("SELECT recent_commands FROM users WHERE LOWER(username) = ?",
                                   (s["username"].lower(),)).fetchone()
                if row and row["recent_commands"]:
                    cmds = json.loads(row["recent_commands"])
                    last_cmds = cmds[-5:] if cmds else []
                    err_cmds = [c for c in last_cmds if "ERROR" in c.upper() or "BŁĄD" in c.upper()]
                    if err_cmds:
                        stuck.append({
                            "username": s["username"],
                            "first_name": s["first_name"],
                            "last_cmd": last_cmds[-1],
                            "sp": s["science_points"]
                        })

        return {
            "class_code": c_code,
            "class_name": cls_info["name"],
            "owner_teacher": cls_info["owner_teacher"],
            "students_count": cnt,
            "avg_sp": avg_sp,
            "ranking": students[:10],
            "recent_stuck_students": stuck[:5]
        }

    # =========================================================================
    # METODY ZARZĄDZANIA KONTAMI (ADMIN / NAUCZYCIEL)
    # =========================================================================

    def get_user_role(self, username: str) -> str:
        """Zwraca rolę użytkownika ('admin', 'teacher', 'student')."""
        safe_name = username.strip().lower()
        with self._get_connection() as conn:
            row = conn.execute("SELECT role FROM users WHERE LOWER(username) = ?", (safe_name,)).fetchone()
            if row and "role" in row.keys() and row["role"]:
                return str(row["role"]).lower()
            return "student"

    def set_user_role(self, username: str, new_role: str) -> bool:
        """Zmienia rolę użytkownika na 'student', 'teacher' lub 'admin'."""
        role_clean = new_role.strip().lower()
        if role_clean not in ("student", "teacher", "admin"):
            return False

        safe_name = username.strip().lower()
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE LOWER(username) = ?", (safe_name,)).fetchone()
            if not row:
                return False
            data = self._row_to_user_data(row)
            data["role"] = role_clean
            conn.execute("""
                UPDATE users SET role = ?, data_json = ?, updated_at = CURRENT_TIMESTAMP
                WHERE LOWER(username) = ?;
            """, (role_clean, json.dumps(data, ensure_ascii=False), safe_name))
            conn.commit()
            return True

    def reset_password(self, username: str, new_password: str) -> bool:
        """Ustawia nowe hasło dla użytkownika."""
        if not new_password:
            return False
        safe_name = username.strip().lower()
        new_hash = self._hash_password(new_password)
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE LOWER(username) = ?", (safe_name,)).fetchone()
            if not row:
                return False
            data = self._row_to_user_data(row)
            data["password_hash"] = new_hash
            conn.execute("""
                UPDATE users SET password_hash = ?, data_json = ?, updated_at = CURRENT_TIMESTAMP
                WHERE LOWER(username) = ?;
            """, (new_hash, json.dumps(data, ensure_ascii=False), safe_name))
            conn.commit()
            return True

    def adjust_user_sp(self, username: str, points: int, is_delta: bool = True) -> int | None:
        """Modyfikuje lub ustawia punkty Nauki (SP) gracza."""
        safe_name = username.strip().lower()
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE LOWER(username) = ?", (safe_name,)).fetchone()
            if not row:
                return None
            data = self._row_to_user_data(row)
            old_sp = int(data.get("science_points", 0))
            new_sp = max(0, (old_sp + points) if is_delta else points)
            data["science_points"] = new_sp
            conn.execute("""
                UPDATE users SET science_points = ?, data_json = ?, updated_at = CURRENT_TIMESTAMP
                WHERE LOWER(username) = ?;
            """, (new_sp, json.dumps(data, ensure_ascii=False), safe_name))
            conn.commit()
            return new_sp

    def count_teacher_students(self, teacher_username: str) -> int:
        """Zwraca liczbę uczniów powiązanych z danym nauczycielem."""
        safe_name = teacher_username.strip().lower()
        with self._get_connection() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM users WHERE LOWER(owner_teacher) = ?", (safe_name,)).fetchone()
            return int(row["cnt"]) if row else 0

    def get_teacher_max_students(self, teacher_username: str) -> int:
        """Zwraca maksymalny limit uczniów przypisany do konta nauczyciela."""
        safe_name = teacher_username.strip().lower()
        with self._get_connection() as conn:
            row = conn.execute("SELECT max_students FROM users WHERE LOWER(username) = ?", (safe_name,)).fetchone()
            if row and row["max_students"] is not None:
                return int(row["max_students"])
            return 50

    def list_users(self, query: str = "", role_filter: str = None, teacher_filter: str = None) -> list[dict]:
        """Wyszukuje i zwraca podsumowanie użytkowników (do panelu admina/nauczyciela)."""
        safe_q = f"%{query.strip().lower()}%" if query else "%"
        role_clean = role_filter.strip().lower() if role_filter else None
        teacher_clean = teacher_filter.strip().lower() if teacher_filter else None

        with self._get_connection() as conn:
            params = [safe_q, safe_q, safe_q]
            where = "(LOWER(username) LIKE ? OR LOWER(first_name) LIKE ? OR LOWER(last_name) LIKE ?)"
            if role_clean:
                where += " AND LOWER(role) = ?"
                params.append(role_clean)
            if teacher_clean:
                where += " AND LOWER(owner_teacher) = ?"
                params.append(teacher_clean)

            sql = f"""
                SELECT username, first_name, last_name, age, role, owner_teacher, science_points,
                       professor_hints, completed_tasks, completed_quizzes, created_at
                FROM users
                WHERE {where}
                ORDER BY role DESC, username ASC;
            """
            rows = conn.execute(sql, params).fetchall()

            res = []
            for r in rows:
                c_tasks = json.loads(r["completed_tasks"]) if r["completed_tasks"] else []
                c_quizzes = json.loads(r["completed_quizzes"]) if r["completed_quizzes"] else []
                c_rows = conn.execute("""
                    SELECT c.code FROM classes c
                    JOIN class_members m ON c.id = m.class_id
                    WHERE LOWER(m.username) = ?
                    ORDER BY c.code ASC
                """, (r["username"].lower(),)).fetchall()
                classes_list = [cr["code"] for cr in c_rows]

                res.append({
                    "username": r["username"],
                    "first_name": r["first_name"],
                    "last_name": r["last_name"],
                    "age": r["age"],
                    "role": r["role"] if ("role" in r.keys() and r["role"]) else "student",
                    "owner_teacher": r["owner_teacher"] if ("owner_teacher" in r.keys() and r["owner_teacher"]) else None,
                    "classes": classes_list,
                    "science_points": r["science_points"],
                    "professor_hints": r["professor_hints"],
                    "tasks_count": len(c_tasks),
                    "quizzes_count": len(c_quizzes),
                    "created_at": str(r["created_at"])[:16] if r["created_at"] else ""
                })
            return res

    def get_user_summary(self, username: str) -> dict | None:
        """Zwraca szczegółową kartę danego użytkownika z listą zadań i rozdziałów."""
        safe_name = username.strip().lower()
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM users WHERE LOWER(username) = ?", (safe_name,)).fetchone()
            if not row:
                return None
            u = self._row_to_user_data(row)
            classes = self.get_student_classes(safe_name)
            return {
                "username": u.get("username"),
                "first_name": u.get("first_name"),
                "last_name": u.get("last_name"),
                "age": u.get("age"),
                "role": u.get("role", "student"),
                "owner_teacher": u.get("owner_teacher"),
                "classes": classes,
                "science_points": u.get("science_points", 0),
                "professor_hints": u.get("professor_hints", 1),
                "unlocked_techs": u.get("unlocked_techs", []),
                "completed_tasks": u.get("completed_tasks", []),
                "completed_quizzes": u.get("completed_quizzes", []),
                "tasks_count": len(u.get("completed_tasks", [])),
                "quizzes_count": len(u.get("completed_quizzes", [])),
                "created_at": str(row["created_at"]) if "created_at" in row.keys() else ""
            }
