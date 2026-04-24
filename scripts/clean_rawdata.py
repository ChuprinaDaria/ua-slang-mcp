"""
Скрипт чистки raw markdown → structured JSON.
Парсить rowdata*.md файли і генерує:
  - data/streaks.json  (стійкі вирази/шаблони)
  - data/slang.json    (актуальний сленг)
  - data/memes_active.json (динамічні меми)
"""

import json
import re
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Engagement-шаблони, які ЗАВЖДИ актуальні → streak, не meme
STREAK_PATTERNS = {
    "Непопулярна думка",
    "Осуджуємо і не слухаємо",
    "Слухаємо і не засуджуємо",
    "Стрем або норм",
    "Краш або кринж",
    "Питання до залу",
    "Я з тих людей",
    "Розкажіть",
    "Кому цікаво",
    "Хто ще такий",
    "Рандомний факт про мене",
    "Моя токсична риса",
    "Посилання в шапці профілю",
    "Давайте зробимо нетворкінг",
    "Ну що, залітай знайомитись",
}

# Частота тексту → score 1-10
FREQ_MAP = {
    "дуже висока": 9,
    "висока": 7,
    "середня-висока": 6,
    "середня–висока": 6,
    "середня": 5,
    "низька-середня": 3,
    "низька–середня": 3,
    "середня-низька": 3,
    "середня–низька": 3,
    "низька": 2,
}


def parse_frequency(text: str) -> int:
    """'~3-4 на сторінку; середня-висока' → 6"""
    text = text.lower().strip()
    for key, score in FREQ_MAP.items():
        if key in text:
            return score
    return 5  # default


def parse_section(text: str) -> list[dict]:
    """Парсить один розділ markdown → список записів."""
    entries = []
    # Шукаємо записи за патерном: число. слово/фраза
    blocks = re.split(r"\n(?=\d+\.\s)", text)

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # Перша лінія — заголовок
        lines = block.split("\n")
        header_match = re.match(r"(\d+)\.\s+(.+)", lines[0])
        if not header_match:
            continue

        title = header_match.group(2).strip().strip('"').strip("«»")

        entry = {
            "title": title,
            "meaning": "",
            "context": "",
            "example": "",
            "frequency_score": 5,
            "tags": [],
            "raw_block": block,
        }

        for line in lines[1:]:
            line = line.strip()
            if line.startswith("Значення:"):
                entry["meaning"] = line.replace("Значення:", "").strip()
            elif line.startswith("Контекст:"):
                entry["context"] = line.replace("Контекст:", "").strip()
                # Витягуємо приклади з контексту
                examples = re.findall(r"[««](.+?)[»»]|'(.+?)'", entry["context"])
                if examples:
                    entry["example"] = next(
                        e[0] or e[1] for e in examples if e[0] or e[1]
                    )
            elif line.startswith("Частота:"):
                entry["frequency_score"] = parse_frequency(
                    line.replace("Частота:", "")
                )
            elif line.startswith("Тип:"):
                entry["tags"].append(line.replace("Тип:", "").strip())
            elif line.startswith("Морфологія:"):
                entry["tags"].append(f"морфологія: {line.replace('Морфологія:', '').strip()}")
            elif line.startswith("Похідні:"):
                entry["tags"].append(f"похідні: {line.replace('Похідні:', '').strip()}")
            elif line.startswith("Примітка:"):
                entry["tags"].append(f"примітка: {line.replace('Примітка:', '').strip()}")

        entries.append(entry)

    return entries


def detect_section_type(header: str) -> str:
    """Визначає тип розділу за заголовком."""
    header_lower = header.lower()
    if "сленг" in header_lower:
        return "slang"
    elif "суржик" in header_lower:
        return "surzhyk"
    elif "мем" in header_lower:
        return "meme"
    return "unknown"


def is_streak(entry: dict, section_type: str) -> bool:
    """Чи це streak (стійкий вираз), а не динамічний мем."""
    title = entry["title"]
    # Engagement-шаблони — це streak
    for pattern in STREAK_PATTERNS:
        if pattern.lower() in title.lower():
            return True
    # Якщо це мем-розділ але frequency дуже висока і немає lifecycle — streak
    if section_type == "meme" and entry["frequency_score"] >= 8:
        return True
    return False


def build_slang_entry(entry: dict, idx: int) -> dict:
    return {
        "id": f"slang_{idx:03d}",
        "word": entry["title"],
        "meaning": entry["meaning"],
        "example": entry["example"] or entry["context"],
        "first_seen": "2024-01-01",
        "last_seen": date.today().isoformat(),
        "frequency_score": entry["frequency_score"],
        "frequency_trend": "stable",
        "category": "general",
        "tags": entry["tags"],
        "status": "active",
    }


def build_streak_entry(entry: dict, idx: int) -> dict:
    return {
        "id": f"streak_{idx:03d}",
        "phrase": entry["title"],
        "meaning": entry["meaning"],
        "context": entry["context"],
        "example": entry["example"] or entry["context"],
        "first_seen": "2024-01-01",
        "source_count": entry["frequency_score"] * 100,
        "category": "engagement" if "шаблон" in " ".join(entry["tags"]).lower() else "expression",
        "tags": entry["tags"],
        "status": "active",
    }


def build_meme_entry(entry: dict, idx: int) -> dict:
    # Спробуємо витягти шаблон
    template = ""
    title = entry["title"]
    if "..." in title or "___" in title:
        template = title
    elif ":" in title:
        template = title.split(":")[0] + ": {тема}"

    return {
        "id": f"meme_{idx:03d}",
        "title": entry["title"],
        "format": "text_phrase",
        "description": entry["meaning"],
        "example": entry["example"] or entry["context"],
        "template": template,
        "first_seen": "2026-04-01",
        "last_seen": date.today().isoformat(),
        "frequency_score": entry["frequency_score"],
        "frequency_trend": "stable",
        "lifecycle_stage": "active",
        "virality_score": round(entry["frequency_score"] * 0.8, 1),
        "category": "reaction",
        "tags": entry["tags"],
        "status": "active",
    }


def process_rawdata(filepath: Path) -> dict:
    """Парсить один raw файл → {slang: [], streaks: [], memes: []}"""
    text = filepath.read_text(encoding="utf-8")

    result = {"slang": [], "streaks": [], "memes": []}

    # Розбиваємо на розділи
    sections = re.split(r"(?=РОЗДІЛ \d+)", text)

    for section in sections:
        if not section.strip():
            continue

        # Визначаємо тип — підтримуємо заголовки з і без емоджі
        header_match = re.match(r"РОЗДІЛ \d+\s*—\s*(.+?)(?:\n|$)", section)
        if not header_match:
            continue

        header_text = header_match.group(1).strip()
        section_type = detect_section_type(header_text)
        entries = parse_section(section)

        for entry in entries:
            if section_type == "surzhyk":
                # Суржик → slang з тегом "суржик"
                entry["tags"].append("суржик")
                result["slang"].append(entry)
            elif section_type == "meme":
                if is_streak(entry, section_type):
                    result["streaks"].append(entry)
                else:
                    result["memes"].append(entry)
            elif section_type == "slang":
                result["slang"].append(entry)

    return result


def load_existing(filename: str) -> tuple[list[dict], set[str]]:
    """Завантажує існуючий JSON і повертає (записи, множина title)."""
    path = DATA_DIR / filename
    if not path.exists():
        return [], set()
    data = json.loads(path.read_text(encoding="utf-8"))
    # Ключ для дедуплікації
    titles = set()
    for item in data:
        key = (item.get("word") or item.get("phrase") or item.get("title", "")).lower().strip()
        titles.add(key)
    return data, titles


def main():
    # Збираємо всі raw файли: rowdata*.md + data/raw/*_parsed.md
    raw_files = sorted(PROJECT_ROOT.glob("rowdata*.md"))
    parsed_dir = DATA_DIR / "raw"
    if parsed_dir.exists():
        raw_files.extend(sorted(parsed_dir.glob("*_parsed.md")))

    if not raw_files:
        print("Не знайдено файлів для парсингу")
        sys.exit(1)

    # Завантажуємо існуючі дані — MERGE, не перезапис
    existing_slang, seen_slang = load_existing("slang.json")
    existing_streaks, seen_streaks = load_existing("streaks.json")
    existing_memes, seen_memes = load_existing("memes_active.json")

    seen_titles = seen_slang | seen_streaks | seen_memes
    new_slang = []
    new_streaks = []
    new_memes = []

    for f in raw_files:
        print(f"Парсимо: {f.name}")
        result = process_rawdata(f)

        for category, items in result.items():
            for item in items:
                key = item["title"].lower().strip()
                if key in seen_titles:
                    continue
                seen_titles.add(key)

                if category == "slang":
                    new_slang.append(item)
                elif category == "streaks":
                    new_streaks.append(item)
                elif category == "memes":
                    new_memes.append(item)

    # Будуємо нові записи з правильними ID (продовжуємо нумерацію)
    slang_start = len(existing_slang)
    streaks_start = len(existing_streaks)
    memes_start = len(existing_memes)

    new_slang_out = [build_slang_entry(e, slang_start + i + 1) for i, e in enumerate(new_slang)]
    new_streaks_out = [build_streak_entry(e, streaks_start + i + 1) for i, e in enumerate(new_streaks)]
    new_memes_out = [build_meme_entry(e, memes_start + i + 1) for i, e in enumerate(new_memes)]

    # Оновлюємо last_seen для існуючих active записів
    today = date.today().isoformat()
    for item in existing_slang:
        if item.get("status") == "active":
            item["last_seen"] = today
    for item in existing_memes:
        if item.get("status") == "active":
            item["last_seen"] = today

    # Merge
    all_slang = existing_slang + new_slang_out
    all_streaks = existing_streaks + new_streaks_out
    all_memes = existing_memes + new_memes_out

    # Зберігаємо
    DATA_DIR.mkdir(exist_ok=True)

    for filename, data in [
        ("slang.json", all_slang),
        ("streaks.json", all_streaks),
        ("memes_active.json", all_memes),
    ]:
        path = DATA_DIR / filename
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"✓ {filename}: {len(data)} записів")

    # Метадані пакету
    package = {
        "package_date": today,
        "version": today.replace("-", "."),
        "last_updated": today,
        "stats": {
            "total_slang_active": len([s for s in all_slang if s.get("status") == "active"]),
            "total_streaks": len(all_streaks),
            "total_memes_active": len([m for m in all_memes if m.get("status") == "active"]),
            "new_today": {
                "slang": len(new_slang_out),
                "streaks": len(new_streaks_out),
                "memes": len(new_memes_out),
            },
        },
        "parsing_source": "threads",
    }
    pkg_path = DATA_DIR / "packages" / f"{today}.json"
    pkg_path.parent.mkdir(exist_ok=True)
    pkg_path.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ package: {pkg_path.name}")

    print(f"\nВсього: {len(all_slang)} сленг + {len(all_streaks)} стрік + {len(all_memes)} мемів")
    print(f"Нових сьогодні: +{len(new_slang_out)} сленг, +{len(new_streaks_out)} стрік, +{len(new_memes_out)} мемів")


if __name__ == "__main__":
    main()
