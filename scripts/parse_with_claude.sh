#!/bin/bash
# Передає зібрані пости в Claude CLI для структуризації.
# Usage: ./scripts/parse_with_claude.sh [date]
# Default: сьогоднішня дата

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TODAY="${1:-$(date +%Y-%m-%d)}"
RAW_FILE="$PROJECT_ROOT/data/raw/$TODAY.txt"
OUTPUT_FILE="$PROJECT_ROOT/data/raw/${TODAY}_parsed.md"

if [ ! -f "$RAW_FILE" ]; then
    echo "❌ Файл $RAW_FILE не знайдено. Спочатку запусти scrape_threads.py"
    exit 1
fi

echo "📝 Парсимо $RAW_FILE через Claude CLI..."

# Existing data для контексту — щоб Claude не додавав дублі
EXISTING_SLANG=$(python3 -c "
import json;
data = json.load(open('$PROJECT_ROOT/data/slang.json'));
print(', '.join(item['word'] for item in data[:50]))
" 2>/dev/null || echo "")

EXISTING_MEMES=$(python3 -c "
import json;
data = json.load(open('$PROJECT_ROOT/data/memes_active.json'));
print(', '.join(item['title'] for item in data[:30]))
" 2>/dev/null || echo "")

# Claude CLI парсить raw text
claude -p "$(cat <<PROMPT
Ти — лінгвістичний парсер української інтернет-мови.

Ось пости з Threads зібрані сьогодні ($TODAY).
Проаналізуй їх і витягни ТІЛЬКИ НОВІ одиниці (слова, вирази, меми).

## Вже є в базі (НЕ ДОДАВАЙ):
Сленг: $EXISTING_SLANG
Меми: $EXISTING_MEMES

## Формат виводу — СТРОГО такий:

РОЗДІЛ 1 — СУЧАСНИЙ СЛЕНГ
[номер]. [слово/фраза]
Значення: [що означає]
Контекст: [цитата з поста де зустрілось]
Частота: [низька / середня / висока / дуже висока]

РОЗДІЛ 2 — СУРЖИК
[той самий формат]

РОЗДІЛ 3 — МЕМНІ ФРАЗИ
[той самий формат]

## Правила:
- ТІЛЬКИ нове, чого немає в базі вище
- Мінімум 3 символи у слові
- Контекст — реальна цитата з поста
- Якщо нічого нового — напиши "НОВИХ ОДИНИЦЬ НЕ ЗНАЙДЕНО"
- Engagement-шаблони ("Непопулярна думка:", "Питання до залу:") → РОЗДІЛ 3
- Суржик = змішування укр+рос в одному вислові

## Пости:
$(cat "$RAW_FILE")
PROMPT
)" > "$OUTPUT_FILE"

# Перевіряємо результат
if grep -q "НОВИХ ОДИНИЦЬ НЕ ЗНАЙДЕНО" "$OUTPUT_FILE"; then
    echo "ℹ️  Нових одиниць не знайдено"
    rm "$OUTPUT_FILE"
    exit 0
fi

LINES=$(wc -l < "$OUTPUT_FILE")
echo "✓ Знайдено нові одиниці → ${OUTPUT_FILE} ($LINES рядків)"
echo "  Далі: python scripts/clean_rawdata.py оновить JSON"
