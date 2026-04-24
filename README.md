# ua-slang-mcp

**MCP server for live Ukrainian internet language — slang, memes, and phrases for AI agents.**

[Українська](#-українська) | [English](#-english)

---

## 🇬🇧 English

### What is this?

AI agents write dead language. "This is not just a product — it's a solution." Long dashes, bureaucratic tone, templates.

Real Ukrainians on the internet write differently:
- **"капець, це кринж"** — not "this causes a feeling of discomfort"
- **"залітай знайомитись"** — not "we invite you to join our community"
- **"горить жопа від дедлайнів"** — not "I'm experiencing increased workload"
- **"крч, скіпнула мітинг"** — not "unfortunately, I missed the meeting"

**ua-slang-mcp** gives AI agents access to a living dictionary, updated daily from Threads. With dates, trends, and freshness checks — so your agents never use dead memes.

### Install

```bash
npm install ua-slang-mcp
```

### Connect to Claude Code

```bash
# Option 1: npx (always latest)
claude mcp add ua-slang -- npx ua-slang-mcp

# Option 2: after npm install
claude mcp add ua-slang -- node node_modules/ua-slang-mcp/dist/server.js
```

### Three data streams

| Stream | What | Updates |
|--------|------|---------|
| **Slang** | Active words with aging tracking | Daily frequency check |
| **Streak** | Stable expressions/templates, always relevant | Only added, never expire |
| **Memes** | Dynamic trends with lifecycle | Aggressive tracking: rising → peak → dead |

### Tools

| Tool | Description |
|------|-------------|
| `get_dataset_info` | Dataset size, last update date, coverage |
| `search_slang(query)` | Search slang — meaning, example, freshness |
| `search_streaks(query)` | Search stable expressions |
| `get_trending_memes(limit)` | Top memes by virality_score |
| `get_trending_slang(limit)` | Rising slang |
| `suggest_for_post(topic)` | Suggest slang/memes for a post topic |
| `check_freshness(word)` | Is this word still relevant? (verdict: safe/outdated/dead) |
| `get_daily_package()` | Daily update package: what's new, what's deprecated |
| `get_all_slang()` | All active slang with dates |
| `get_all_streaks()` | All stable expressions |

Every response includes:
- `_dataset_last_updated` — last dataset update date
- `_freshness` — today / this_week / this_month / stale
- `verdict` — safe to use / outdated / dead meme

### How it works

```
Daily cron
  → Playwright scrapes Threads
  → Claude CLI parses posts, finds new words/memes
  → Cleanup script: deduplication, merge with existing data
  → npm publish → users get fresh data on next install/update
```

### Auto-updates

The npm package is published daily with fresh data. To get updates:

```bash
# Always latest via npx
npx ua-slang-mcp@latest

# Or update manually
npm update ua-slang-mcp
```

### Contributing

Dataset is currently **152 entries** and growing daily. Help needed:

- **New words/memes** — see something fresh on Threads/TikTok/X? Open a PR or issue
- **New sources** — TikTok comments, X/Twitter UA, Reddit UA
- **Niche slang** — IT, psychology, parenting, business, gaming, military
- **Tests** — coverage for parser and MCP tools
- **Integrations** — other AI platforms

#### How to contribute

1. Fork → branch → PR
2. Or just create an issue with a new word/meme
3. Format for new entries — see `DATASET_STRUCTURE.md`

**Your data is welcome in any format.** Got a list of slang words in a Google Doc, a CSV, a screenshot, raw JSON, or just a messy text dump? Submit it via PR — we'll sort it out. Any format, any structure, any size. The more sources, the richer the dataset.

---

## 🇺🇦 Українська

### Що це?

AI-агенти пишуть мертвою мовою. "Це не просто продукт — це рішення". Довге тире, канцелярит, шаблони.

Реальні українці в інтернеті пишуть інакше:
- **"капець, це кринж"** — а не "це викликає відчуття незручності"
- **"залітай знайомитись"** — а не "запрошуємо до нашої спільноти"
- **"горить жопа від дедлайнів"** — а не "відчуваю підвищене навантаження"
- **"крч, скіпнула мітинг"** — а не "на жаль, я пропустила зустріч"

**ua-slang-mcp** дає AI-агентам доступ до живого словника, який оновлюється щодня з Threads. З датами, трендами, і перевіркою актуальності — щоб не використовувати мертві меми.

### Встановлення

```bash
npm install ua-slang-mcp
```

### Підключення до Claude Code

```bash
# Варіант 1: npx (завжди остання версія)
claude mcp add ua-slang -- npx ua-slang-mcp

# Варіант 2: після npm install
claude mcp add ua-slang -- node node_modules/ua-slang-mcp/dist/server.js
```

### Три напрямки даних

| Напрямок | Що це | Оновлення |
|----------|-------|-----------|
| **Сленг** | Актуальні слова з трекінгом старіння | Щоденна перевірка частоти |
| **Стрік** | Стійкі вирази/шаблони, завжди актуальні | Тільки додаються, ніколи не старіють |
| **Меми** | Динамічні тренди з lifecycle | Агресивний трекінг: rising → peak → dead |

### Tools

| Tool | Опис |
|------|------|
| `get_dataset_info` | Розмір датасету, дата оновлення |
| `search_slang(query)` | Пошук сленгу — значення, приклад, freshness |
| `search_streaks(query)` | Пошук стійких виразів |
| `get_trending_memes(limit)` | Топ мемів за virality_score |
| `get_trending_slang(limit)` | Сленг що росте |
| `suggest_for_post(topic)` | Підказки сленгу/мемів для теми поста |
| `check_freshness(word)` | Чи слово ще актуальне (verdict: safe/outdated/dead) |
| `get_daily_package()` | Щоденний пакет оновлень |
| `get_all_slang()` | Весь активний сленг з датами |
| `get_all_streaks()` | Всі стійкі вирази |

### Автооновлення

npm-пакет публікується щодня зі свіжими даними. Щоб отримувати оновлення:

```bash
# Завжди остання версія через npx
npx ua-slang-mcp@latest

# Або оновити вручну
npm update ua-slang-mcp
```

### Контрибуції

Датасет зараз **152 записи** і росте щодня. Потрібна допомога:

- **Нові слова/меми** — бачиш щось свіже? Кидай PR або issue
- **Нові джерела** — TikTok, X/Twitter UA, Reddit UA
- **Нішевий сленг** — IT, психологія, мами, бізнес, геймінг, ЗСУ
- **Тести** — покриття для парсера і MCP tools

**Дані у будь-якому форматі — welcome.** Є список слів у Google Doc, CSV, скрін, JSON, просто текстовий файл? Кидай PR — розберемось. Будь-який формат, будь-яка структура, будь-який розмір. Чим більше джерел — тим живіший датасет.

---

## Contacts

**Lazysoft** — [lazysoft.pl](https://lazysoft.pl)

- Telegram: [@dcprn](https://t.me/dcprn)
- WhatsApp: [Chat](https://wa.me/message/36I75JLAUHYKJ1)
- Email: [dchuprina@lazysoft.pl](mailto:dchuprina@lazysoft.pl)

Author: **Daria Chuprina**

## License

MIT
