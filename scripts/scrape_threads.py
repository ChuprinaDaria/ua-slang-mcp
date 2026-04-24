"""
Playwright скрипт для скрапінгу Threads.
Відкриває пошук за ключовими словами, збирає текст постів.
Зберігає в data/raw/YYYY-MM-DD.txt

Використання:
  python scripts/scrape_threads.py
  python scripts/scrape_threads.py --headed  # з видимим браузером
  python scripts/scrape_threads.py --keywords "кринж,вайб,зашквар"
"""

import argparse
import json
from datetime import date, datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"

# Ключові слова для пошуку — покривають всі 3 напрямки
DEFAULT_KEYWORDS = [
    # Сленг-тригери
    "кринж",
    "вайб",
    "зашквар",
    "токсик",
    "флексити",
    "чілити",
    "хейт",
    "скіпати",
    "краш",
    # Суржик-тригери
    "шо за",
    "нормасно",
    "по ходу",
    "ваще",
    "крч",
    # Мем-тригери
    "непопулярна думка",
    "моя токсична риса",
    "стрем або норм",
    "питання до залу",
    # Загальні — для ловлі нового
    "українською",
    "тредс",
    "айтішці",
]

THREADS_SEARCH_URL = "https://www.threads.net/search?q={query}&serp_type=default"


def scrape_keyword(page, keyword: str, max_scrolls: int = 5) -> list[dict]:
    """Скрапить пости за одним ключовим словом."""
    url = THREADS_SEARCH_URL.format(query=keyword.replace(" ", "+"))
    posts = []

    try:
        page.goto(url, wait_until="networkidle", timeout=15000)
        page.wait_for_timeout(2000)
    except Exception as e:
        print(f"  ⚠ Не вдалось завантажити '{keyword}': {e}")
        return posts

    # Скролимо щоб підвантажити пости
    for scroll in range(max_scrolls):
        page.evaluate("window.scrollBy(0, window.innerHeight * 2)")
        page.wait_for_timeout(1500)

    # Збираємо текст постів
    # Threads рендерить пости в div з data-pressable-container
    # або в span всередині article-подібних блоків
    selectors = [
        '[data-pressable-container="true"] span',
        'div[role="main"] span',
        "article span",
    ]

    seen_texts = set()
    for selector in selectors:
        elements = page.query_selector_all(selector)
        for el in elements:
            text = el.inner_text().strip()
            # Фільтруємо: мінімум 15 символів, не дублі, не UI елементи
            if (
                len(text) >= 15
                and text not in seen_texts
                and not text.startswith("Log in")
                and not text.startswith("Sign up")
                and "cookie" not in text.lower()
            ):
                seen_texts.add(text)
                posts.append(
                    {
                        "text": text,
                        "keyword": keyword,
                        "scraped_at": datetime.now().isoformat(),
                    }
                )

        if posts:
            break  # Знайшли робочий селектор

    return posts


def main():
    parser = argparse.ArgumentParser(description="Scrape Threads posts")
    parser.add_argument("--headed", action="store_true", help="Показувати браузер")
    parser.add_argument("--keywords", type=str, help="Ключові слова через кому")
    parser.add_argument("--max-scrolls", type=int, default=5, help="Скільки разів скролити")
    parser.add_argument(
        "--cookies",
        type=str,
        default=str(PROJECT_ROOT / "cookies.json"),
        help="Шлях до cookies.json (для авторизації)",
    )
    args = parser.parse_args()

    keywords = args.keywords.split(",") if args.keywords else DEFAULT_KEYWORDS
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    output_file = RAW_DIR / f"{today}.json"
    all_posts = []

    print(f"Скрапимо Threads: {len(keywords)} ключових слів")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not args.headed,
            args=["--disable-blink-features=AutomationControlled"],
        )

        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            locale="uk-UA",
        )

        # Підвантажуємо cookies якщо є (для авторизованого доступу)
        cookies_path = Path(args.cookies)
        if cookies_path.exists():
            cookies = json.loads(cookies_path.read_text())
            context.add_cookies(cookies)
            print("✓ Cookies завантажено")

        page = context.new_page()

        for i, keyword in enumerate(keywords, 1):
            print(f"[{i}/{len(keywords)}] Шукаю: '{keyword}'", end=" ")
            posts = scrape_keyword(page, keyword, max_scrolls=args.max_scrolls)
            all_posts.extend(posts)
            print(f"→ {len(posts)} постів")

        browser.close()

    # Дедуплікація за текстом
    seen = set()
    unique_posts = []
    for post in all_posts:
        if post["text"] not in seen:
            seen.add(post["text"])
            unique_posts.append(post)

    # Зберігаємо
    output_file.write_text(
        json.dumps(unique_posts, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    # Також зберігаємо plain text для Claude CLI
    txt_file = RAW_DIR / f"{today}.txt"
    txt_file.write_text(
        "\n---\n".join(p["text"] for p in unique_posts), encoding="utf-8"
    )

    print(f"\n✓ {len(unique_posts)} унікальних постів → {output_file.name}")
    print(f"✓ Plain text → {txt_file.name}")


if __name__ == "__main__":
    main()
