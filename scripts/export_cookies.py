"""
Експорт cookies з браузера для Threads.
Відкриває браузер → логінишся в Threads → cookies зберігаються.

Usage:
  python scripts/export_cookies.py
"""

import json
from pathlib import Path

from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).parent.parent
COOKIES_FILE = PROJECT_ROOT / "cookies.json"


def main():
    print("Відкриваю браузер...")
    print("1. Залогінся в Threads (через Instagram)")
    print("2. Переконайся що бачиш стрічку")
    print("3. Закрий браузер (Ctrl+C тут або просто закрий вікно)")
    print()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="uk-UA",
        )

        page = context.new_page()
        page.goto("https://www.threads.net/login")

        print("Чекаю поки залогінишся... (закрий браузер коли готово)")

        try:
            # Чекаємо поки юзер закриє або поки з'явиться головна
            page.wait_for_url("**/threads.net/**", timeout=300000)
            # Даємо час на повний логін
            page.wait_for_timeout(5000)
        except Exception:
            pass

        # Зберігаємо cookies
        cookies = context.cookies()
        COOKIES_FILE.write_text(
            json.dumps(cookies, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\n✓ Збережено {len(cookies)} cookies → {COOKIES_FILE}")

        browser.close()


if __name__ == "__main__":
    main()
