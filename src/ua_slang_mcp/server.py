"""
MCP сервер — сучасна українська інтернет-мова.
Підтримує stdio та HTTP транспорт.
"""

import json
from datetime import date, datetime
from pathlib import Path

from fastmcp import FastMCP

DATA_DIR = Path(__file__).parent.parent.parent / "data"

mcp = FastMCP(
    "UA Slang",
    instructions="Сучасна українська інтернет-мова: сленг, стійкі вирази, меми. "
    "Для AI-агентів у маркетингу та SMM. "
    "Дані оновлюються щодня з Threads. "
    "Кожен запис містить дати — перевіряйте last_seen і frequency_trend для актуальності.",
)


def _load(filename: str) -> list[dict]:
    path = DATA_DIR / filename
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def _dataset_meta() -> dict:
    """Метадані датасету — дата останнього оновлення, розміри."""
    packages_dir = DATA_DIR / "packages"
    last_update = "unknown"
    if packages_dir.exists():
        files = sorted(packages_dir.glob("*.json"), reverse=True)
        if files:
            last_update = files[0].stem  # YYYY-MM-DD

    return {
        "_dataset_last_updated": last_update,
        "_dataset_checked_at": datetime.now().isoformat(timespec="seconds"),
    }


def _with_meta(response: dict | list) -> dict:
    """Обгортає відповідь метаданими датасету."""
    meta = _dataset_meta()
    if isinstance(response, list):
        return {**meta, "count": len(response), "items": response}
    return {**meta, **response}


def _days_since(date_str: str) -> int:
    """Скільки днів тому було date_str."""
    try:
        d = date.fromisoformat(date_str)
        return (date.today() - d).days
    except (ValueError, TypeError):
        return -1


def _freshness_label(days: int) -> str:
    if days < 0:
        return "unknown"
    if days <= 1:
        return "today"
    if days <= 7:
        return "this_week"
    if days <= 30:
        return "this_month"
    if days <= 90:
        return "recent"
    return "stale"


def _enrich_item(item: dict) -> dict:
    """Додає freshness інфо до кожного запису."""
    enriched = dict(item)
    last_seen = item.get("last_seen", item.get("first_seen", ""))
    if last_seen:
        days = _days_since(last_seen)
        enriched["_days_since_seen"] = days
        enriched["_freshness"] = _freshness_label(days)
    return enriched


@mcp.tool
def search_slang(query: str, only_active: bool = True) -> dict:
    """Пошук сленгу за словом або значенням. Кожен результат містить _freshness (today/this_week/this_month/recent/stale).

    Args:
        query: слово або частина значення для пошуку
        only_active: показувати тільки активний сленг (default: True)
    """
    q = query.lower()
    results = []
    for item in _load("slang.json"):
        if only_active and item.get("status") != "active":
            continue
        if q in item["word"].lower() or q in item.get("meaning", "").lower():
            results.append(_enrich_item(item))
    return _with_meta(results)


@mcp.tool
def search_streaks(query: str) -> dict:
    """Пошук стійких виразів/фраз за текстом. Стрік = завжди актуальний вираз.

    Args:
        query: фраза або частина для пошуку
    """
    q = query.lower()
    results = []
    for item in _load("streaks.json"):
        if (
            q in item["phrase"].lower()
            or q in item.get("meaning", "").lower()
            or q in item.get("context", "").lower()
        ):
            results.append(item)
    return _with_meta(results)


@mcp.tool
def get_trending_memes(limit: int = 10) -> dict:
    """Топ мемів зараз за virality_score. Включає _freshness для кожного мему — використовуйте тільки fresh меми для контенту.

    Args:
        limit: кількість мемів (default: 10)
    """
    memes = _load("memes_active.json")
    memes.sort(key=lambda x: x.get("virality_score", 0), reverse=True)
    return _with_meta([_enrich_item(m) for m in memes[:limit]])


@mcp.tool
def get_trending_slang(limit: int = 10) -> dict:
    """Сленг що зараз росте (frequency_trend = rising). Якщо немає rising — топ за frequency_score.

    Args:
        limit: кількість записів (default: 10)
    """
    slang = _load("slang.json")
    rising = [s for s in slang if s.get("frequency_trend") == "rising"]
    if not rising:
        slang.sort(key=lambda x: x.get("frequency_score", 0), reverse=True)
        result = slang[:limit]
    else:
        result = rising[:limit]
    return _with_meta([_enrich_item(s) for s in result])


@mcp.tool
def suggest_for_post(topic: str, style: str = "casual") -> dict:
    """Підказати сленг, стійкі вирази та меми для конкретної теми поста. Повертає тільки свіжі та актуальні одиниці.

    Args:
        topic: тема поста (наприклад: "кава", "робота", "стосунки")
        style: стиль тексту — casual, professional, ironic (default: casual)
    """
    q = topic.lower()

    relevant_slang = []
    for item in _load("slang.json"):
        if item.get("status") != "active":
            continue
        searchable = f"{item['word']} {item.get('meaning', '')} {item.get('example', '')}".lower()
        if q in searchable:
            relevant_slang.append(_enrich_item(item))

    relevant_streaks = []
    for item in _load("streaks.json"):
        searchable = f"{item['phrase']} {item.get('meaning', '')} {item.get('context', '')}".lower()
        if q in searchable:
            relevant_streaks.append(item)

    relevant_memes = []
    for item in _load("memes_active.json"):
        if item.get("status") != "active":
            continue
        searchable = f"{item['title']} {item.get('description', '')} {item.get('example', '')}".lower()
        if q in searchable:
            relevant_memes.append(_enrich_item(item))

    return _with_meta({
        "topic": topic,
        "style": style,
        "slang": relevant_slang[:5],
        "streaks": relevant_streaks[:5],
        "memes": relevant_memes[:3],
        "tip": "Використовуйте тільки елементи з _freshness = today/this_week для актуального контенту",
    })


@mcp.tool
def get_daily_package(package_date: str = "") -> dict:
    """Отримати щоденний пакет оновлень. Містить статистику: скільки нових, скільки deprecated.

    Args:
        package_date: дата у форматі YYYY-MM-DD (default: останній доступний)
    """
    packages_dir = DATA_DIR / "packages"
    if not packages_dir.exists():
        return {"error": "no packages available"}

    if package_date:
        path = packages_dir / f"{package_date}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {"error": f"package for {package_date} not found"}

    files = sorted(packages_dir.glob("*.json"), reverse=True)
    if not files:
        return {"error": "no packages available"}
    return json.loads(files[0].read_text(encoding="utf-8"))


@mcp.tool
def check_freshness(word: str) -> dict:
    """Перевірити чи слово/мем ще актуальне. ОБОВ'ЯЗКОВО викликайте перед використанням слова в контенті.

    Args:
        word: слово або фраза для перевірки
    """
    q = word.lower()

    for item in _load("slang.json"):
        if q in item["word"].lower():
            days = _days_since(item.get("last_seen", ""))
            return _with_meta({
                "word": item["word"],
                "status": item["status"],
                "frequency_score": item["frequency_score"],
                "frequency_trend": item["frequency_trend"],
                "last_seen": item.get("last_seen", "unknown"),
                "_days_since_seen": days,
                "_freshness": _freshness_label(days),
                "is_fresh": item["status"] == "active" and item["frequency_score"] >= 4,
                "verdict": "safe to use" if item["status"] == "active" and item["frequency_score"] >= 4 else "outdated or rare — avoid",
            })

    for item in _load("memes_active.json"):
        if q in item["title"].lower():
            days = _days_since(item.get("last_seen", ""))
            return _with_meta({
                "word": item["title"],
                "status": item["status"],
                "lifecycle_stage": item.get("lifecycle_stage", "unknown"),
                "virality_score": item.get("virality_score", 0),
                "last_seen": item.get("last_seen", "unknown"),
                "_days_since_seen": days,
                "_freshness": _freshness_label(days),
                "is_fresh": item["status"] == "active",
                "verdict": "safe to use" if item["status"] == "active" else "dead meme — don't use",
            })

    return _with_meta({
        "word": word,
        "status": "not_found",
        "is_fresh": False,
        "verdict": "not in database — unknown freshness",
    })


@mcp.tool
def get_all_slang(category: str = "") -> dict:
    """Отримати весь активний сленг з датами. Кожен запис має last_seen і _freshness.

    Args:
        category: фільтр категорії (наприклад: "суржик", "англіцизм"). Порожній = всі.
    """
    slang = [s for s in _load("slang.json") if s.get("status") == "active"]
    if category:
        slang = [s for s in slang if category.lower() in " ".join(s.get("tags", [])).lower()]
    return _with_meta([_enrich_item(s) for s in slang])


@mcp.tool
def get_all_streaks() -> dict:
    """Отримати всі стійкі вирази/шаблони. Стріки завжди актуальні — їх можна використовувати без перевірки freshness."""
    return _with_meta(_load("streaks.json"))


@mcp.tool
def get_dataset_info() -> dict:
    """Інформація про датасет: розмір, дата останнього оновлення, покриття. Викликайте першим щоб зрозуміти актуальність даних."""
    slang = _load("slang.json")
    streaks = _load("streaks.json")
    memes = _load("memes_active.json")

    active_slang = [s for s in slang if s.get("status") == "active"]
    active_memes = [m for m in memes if m.get("status") == "active"]

    return _with_meta({
        "total_entries": len(slang) + len(streaks) + len(memes),
        "slang_active": len(active_slang),
        "slang_deprecated": len(slang) - len(active_slang),
        "streaks": len(streaks),
        "memes_active": len(active_memes),
        "memes_dead": len(memes) - len(active_memes),
        "source": "Threads (threads.net)",
        "language": "Ukrainian internet language (slang + surzhyk + memes)",
        "update_frequency": "daily",
        "usage_hint": "Always call check_freshness() before using slang/memes in content. Streaks are always safe.",
    })


if __name__ == "__main__":
    mcp.run()
