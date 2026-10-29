# KOK BASIC

<p align="center">
  <img width="320" alt="KOK BASIC Logo" src="https://github.com/user-attachments/assets/0fffecb9-8801-4737-a788-7d225009620e" />
</p>

> **K**oduj • **O**dkrywaj • **K**reuj  
> Edukacyjny retro-mikrokomputer webowy i interaktywne drzewo technologii do nauki programowania.

---

## 💡 O Projekcie

**KOK BASIC** to lekka, webowa platforma edukacyjna symulująca klasyczny mikrokomputer retro (w stylu maszyn 8-bitowych z lat 80. i urządzeń PicoCalc / MMBasic), stworzona z myślą o bezstresowej nauce programowania dla dzieci, szkół i pasjonatów retro.

Projekt działa w architekturze **Client-Heavy (Offline-First)**:
* Cały emulator retro (kineskop CRT, interpreter BASIC, edytor programów, wirtualna klawiatura dotykowa i ewaluator zadań) działa w 100% w przeglądarce w JavaScript – bez opóźnień, na komputerach, tabletach i smartfonach.
* Backend w Pythonie (wbudowany standard WSGI `wsgiref` bez zewnętrznych zależności) odpowiada za autoryzację, tokeny sesyjne, ochronę przed atakami brute-force/DDoS, bezpieczną bazę danych uczniów i nauczycieli (SQLite + JSON), synchronizację postępów w chmurze, system klas szkolnych oraz sztuczną inteligencję **Profesora KOK-88**.

---

## ✨ Główne Możliwości

### 📺 1. Kineskop Retro CRT Canvas
* Autentyczny klimat retro: zielony luminofor, linie skanowania (scanlines), poświata i zakrzywienie kineskopu.
* Dynamiczne skalowanie Canvas 2D (pełny ekran, tryby panoramiczne, dostosowanie do ekranów mobilnych).
* Trzy widoki konsoli przełączane komendami i klawiszami funkcyjnymi:
  * **Terminal** – interaktywna linia poleceń.
  * **Edytor kodu (`EDIT`)** – pełnoekranowy edytor programów z numerowaniem linii i kursorem.
  * **Mapa Technologii (`MAP`)** – wizualne drzewo rozwoju umiejętności.

### ⌨️ 2. Zaawansowana Konsola & Autouzupełnianie TAB
* **Autouzupełnianie w stylu IPython**:
  * Jednokrotny `TAB` dopełnia prefiks lub otwiera listę propozycji.
  * Wielokrotny `TAB` przełącza się pomiędzy pasującymi komendami, podkomendami i zmiennymi.
  * Wyraźne wyróżnienie kolorystyczne: komendy i parametry na zielono/turkusowo, a zdefiniowane zmienne użytkownika na ciepły bursztyn z oznaczeniem `[VAR]`.
  * Kontekstowe dopełnianie poleceń wielowyrazowych (`ADMIN ...`, `CLASS ...`, `HELP ...`).
* **Przerwanie `Ctrl+C` (`^C` / Break)**:
  * Natychmiastowe przerwanie oczekiwania na `INPUT`, zatrzymanie pętli programu `RUN`, wyjście z quizu lub wyczyszczenie wpisywanej linii.
* **Historia poleceń**:
  * Strzałki w górę/dół (`↑`/`↓`) po odblokowaniu technologii `HISTORY_1`.

### 🧠 3. Gamifikacja i Drzewo Technologii (221 Zadań)
* **Drzewo wiedzy**: 30+ technologii podzielonych na poziomy (Tier 1–6): od prostego `PRINT`, przez zmienne (`LET`), operacje arytmetyczne, pętle `FOR...NEXT`, warunki `IF...THEN`, po grafikę `GFX`, dźwięki `SOUND`, obsługę pinów `GPIO` i system plików `FILES`.
* **221 interaktywnych zadań**: natychmiastowa weryfikacja kodu z nagrodami w postaci Punktów Nauki (SP).
* **70+ quizów teoretycznych**: utrwalanie wiedzy poprzez pytania z losową kolejnością odpowiedzi.
* **Profesor KOK-88 (AI)**:
  * `HINT` – pomocne podpowiedzi w trudnych momentach dostosowane do wieku ucznia.
  * `CHECK` – profesorska analiza poprawności programu napisanego w edytorze.

### 📱 4. Wirtualna Klawiatura Dotykowa
* Zoptymalizowana pod ekrany dotykowe tabletów i smartfonów.
* Układ literowy (`ABC`) oraz symboli programistycznych (`SYM`).
* Klawisze makr wstawiające często używane komendy, klawisz `TAB` oraz dedykowany przycisk `^C` (Break).

### 🏫 5. Panel Szkoły i Nauczyciela
* Polecenia konsolowe `ADMIN` i `CLASS` z wbudowanym interaktywnym menu:
  * Tworzenie klas i grup uczniów (np. *4A Informatyka*).
  * Masowe generowanie kont uczniów z przyjaznymi hasłami obrazkowo-słownymi.
  * Podgląd postępów w drzewie technologii, zdobytych SP i rozwiązanych quizów.
  * Raporty aktywności i eksport statystyk.

---

## 🏗️ Architektura Projektu

```text
KOK/
├── config/                  # Konfiguracja drzewa technologii i zadań (JSON)
│   ├── tech_tree.json       # Główny indeks technologii
│   └── techs/               # 30+ plików definicji modułów (zadania, quizy, odblokowania)
├── core/                    # Backend Python (lekki, bez zewnętrznych bibliotek okienkowych)
│   ├── user_manager.py      # Zarządzanie użytkownikami, SQLite/JSON, haszowanie, role, sesje, rate-limiter
│   ├── quest_validator.py   # Silnik walidacji zadań i wymagań
│   ├── tech_tree.py         # Loader struktury drzewa technologii
│   ├── player_state.py      # Logika punktów SP i odblokowywania gałęzi
│   └── professor_ai.py      # Integracja z modelem AI Profesora KOK-88
├── www/                     # Aplikacja Webowa
│   ├── app.py               # REST API WSGI (wsgiref) & serwowanie aplikacji
│   ├── wsgi.py              # Punkt wejścia WSGI dla serwerów produkcyjnych
│   └── static/              # Klient Retro (Frontend)
│       ├── js/
│       │   ├── crt_display.js      # Emulator kineskopu CRT Canvas 2D
│       │   ├── basic_engine.js     # Interpreter BASIC w JavaScript
│       │   ├── quest_runner.js     # Obsługa zadań, quizów i drzewa technologii
│       │   └── virtual_keyboard.js # Dotykowa klawiatura wirtualna
│       ├── css/retro.css           # Retro stylistyka kineskopu i responsywność
│       └── index.html              # Główny szablon aplikacji
├── tests/                   # Zestawy testów automatycznych
│   ├── test_user_manager.py        # Testy bazy danych, ról, sesji i limitów logowania
│   ├── test_quest_validator.py     # Testy walidatora + auto-test 221 zadań
│   ├── test_tech_tree.py           # Testy integralności drzewa
│   ├── test_web_app.py             # Testy endpointów REST API, sesji, brute-force i DDoS
│   └── js/                         # Testy frontendu (Node.js test runner)
│       ├── basic_engine.test.js    # Testy interpretera BASIC
│       ├── crt_display.test.js     # Testy wyświetlacza i skrótów TAB / Ctrl+C
│       ├── quest_runner.test.js    # Testy walidatora zadań, quizów i tasowania opcji
│       ├── virtual_keyboard.test.js# Testy klawiatury wirtualnej
│       └── tech_tree_automation.test.js # Test 221 zadań w silniku JS
└── archive/                 # Archiwum historycznych wersji
    └── first_version_with_pc_app_2026_10_28/ # Pierwsza wersja desktopowa Pygame
```

---

## 🚀 Jak Uruchomić Projekt?

### Wymagania:
* **Python 3.10+** (brak konieczności instalowania zewnętrznych bibliotek frameworkowych – backend bazuje na standardowym `wsgiref`)
* Opcjonalnie: **Node.js 18+** (do uruchamiania zestawu testów jednostkowych JavaScript)

### 1. Uruchomienie serwera deweloperskiego:
```bash
python www/app.py
```
Aplikacja będzie dostępna w przeglądarce pod adresem:
👉 **`http://localhost:8080`**

Dla środowiska produkcyjnego (Gunicorn / uWSGI):
```bash
gunicorn wsgi:app --bind 0.0.0.0:8080
```

---

## 🧪 Testy i Jakość Kodu

Projekt kładzie bardzo duży nacisk na stabilność i pokrycie testami zarówno po stronie Pythona, jak i silnika JavaScript w przeglądarce:

### Uruchomienie testów Pythona (Backend):
```bash
pytest
```
* Wszystkie 34 testy wykonują się w ~4 sekundy.
* Pełna automatyczna weryfikacja 221 zadań drzewa technologii.
* Testy sesji, ról administracyjnych, rate limitera brute-force i ochrony anty-DDoS.

### Uruchomienie testów JavaScript (Frontend):
```bash
npm test
```
* Wykorzystuje natywny silnik `node --test`.
* 42 testy sprawdzają interpreter BASIC, kineskop CRT, autouzupełnianie TAB, tasowanie quizów, obsługę `Ctrl+C` oraz przechodzą wszystkie 221 zadań w silniku JS.

### Pokrycie testami (Coverage):
```bash
coverage run --source=core,www -m pytest tests/
coverage report -m
```

---

## 📦 Archiwum Wersji Desktopowej (Pygame)

Historyczna, pierwsza wersja KOK BASIC stworzona jako natywna aplikacja okienkowa w Pythonie z użyciem biblioteki `pygame` została bezpiecznie zarchiwizowana w katalogu:
📁 [`archive/first_version_with_pc_app_2026_10_28/`](archive/first_version_with_pc_app_2026_10_28/) (alias: `archiwum/`).

Zawiera ona kompletny pierwotny kod interpretera desktopowego, emulator CRT Pygame oraz dedykowany zestaw testów. Szczegóły uruchomienia znajdują się w tamtejszym pliku `README.md`.

---

## 📄 Licencja

Projekt objęty jest licencją MIT. Szczegóły w pliku [LICENSE](LICENSE).
