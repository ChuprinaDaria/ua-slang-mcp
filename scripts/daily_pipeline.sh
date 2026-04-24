#!/bin/bash
# ============================================
# Щоденний pipeline: scrape → parse → clean → push
# Запускати через cron:
#   0 8 * * * /home/dchuprina/ua-slang-mcp/scripts/daily_pipeline.sh >> /home/dchuprina/ua-slang-mcp/logs/daily.log 2>&1
# ============================================

set -euo pipefail

PROJECT_ROOT="/home/dchuprina/ua-slang-mcp"
TODAY=$(date +%Y-%m-%d)
LOG_DIR="$PROJECT_ROOT/logs"

mkdir -p "$LOG_DIR"

echo "=========================================="
echo "[$TODAY $(date +%H:%M:%S)] Старт щоденного pipeline"
echo "=========================================="

cd "$PROJECT_ROOT"

# Активуємо venv якщо є
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# ---- КРОК 1: Скрапимо Threads ----
echo ""
echo "▶ КРОК 1: Скрапінг Threads..."
python scripts/scrape_threads.py --max-scrolls 3

RAW_FILE="data/raw/$TODAY.txt"
if [ ! -f "$RAW_FILE" ]; then
    echo "⚠ Raw файл не створено, можливо Threads заблокував. Пробуємо з headed..."
    python scripts/scrape_threads.py --headed --max-scrolls 3
fi

if [ ! -f "$RAW_FILE" ]; then
    echo "❌ Скрапінг не вдався. Завершуємо."
    exit 1
fi

POST_COUNT=$(wc -l < "$RAW_FILE")
echo "✓ Зібрано рядків: $POST_COUNT"

# ---- КРОК 2: Парсимо через Claude CLI ----
echo ""
echo "▶ КРОК 2: Парсинг через Claude CLI..."
bash scripts/parse_with_claude.sh "$TODAY"

PARSED_FILE="data/raw/${TODAY}_parsed.md"
if [ ! -f "$PARSED_FILE" ]; then
    echo "ℹ️  Нових одиниць не знайдено. Оновлюємо дати."
fi

# ---- КРОК 3: Чистка і merge в JSON ----
echo ""
echo "▶ КРОК 3: Чистка і merge..."
python scripts/clean_rawdata.py

# ---- КРОК 4: Git commit і push ----
echo ""
echo "▶ КРОК 4: Git push..."
cd "$PROJECT_ROOT"
git add data/
if git diff --staged --quiet; then
    echo "ℹ️  Немає змін для комміту"
else
    git commit -m "chore: daily update $TODAY"
    git push
    echo "✓ Запушено"
fi

echo ""
echo "=========================================="
echo "[$TODAY $(date +%H:%M:%S)] Pipeline завершено"
echo "=========================================="
