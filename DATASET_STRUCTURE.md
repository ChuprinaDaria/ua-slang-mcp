# UA Internet Mova — Структура датасету

## Огляд

MCP-сервер (HTTP + stdio) для живої української інтернет-мови.
Джерело: щоденний парсинг Threads.
Споживачі: AI-агенти для маркетингу, SMM, копірайтингу.

---

## 3 напрямки даних

### 1. Стрік (Стійкі вирази / фрази)

Вирази, які **завжди актуальні** і не залежать від дати. Постійно розширюється.

```json
{
  "id": "streak_001",
  "phrase": "я в цьому",
  "meaning": "я згодна / я підтримую",
  "context": "універсальне підтвердження",
  "example": "— Йдемо на каву? — Я в цьому",
  "first_seen": "2024-03-15",
  "source_count": 847,
  "category": "agreement",
  "tags": ["розмовне", "підтвердження"],
  "status": "active"
}
```

**Особливості:**
- Ніколи не видаляються, тільки додаються
- `source_count` — скільки разів зустріли у Threads (кумулятивно)
- `status` завжди `active`

---

### 2. Сленг (Актуальний словник)

Слова та вирази, які **зараз у вжитку**. Відстежуємо актуальність — застарілий сленг маркується.

```json
{
  "id": "slang_001",
  "word": "краш",
  "meaning": "людина, в яку закохані / об'єкт захоплення",
  "example": "він мій краш з універу",
  "first_seen": "2023-06-10",
  "last_seen": "2026-04-24",
  "frequency_30d": 234,
  "frequency_trend": "stable",
  "category": "relationships",
  "tags": ["запозичення", "англіцизм"],
  "status": "active",
  "deprecated_since": null,
  "replaced_by": null
}
```

**Особливості:**
- `frequency_trend`: `rising` | `stable` | `declining` | `dead`
- `status`: `active` | `declining` | `deprecated`
- `deprecated_since` — дата, коли частота впала нижче порогу
- `replaced_by` — ID нового сленгу, який замінив цей (якщо є)
- Щоденна перевірка частоти за останні 30 днів

**Логіка старіння:**
- `frequency_30d` < 10 протягом 14 днів → `declining`
- `frequency_30d` = 0 протягом 30 днів → `deprecated`

---

### 3. Меми (Динамічний трекінг)

Меми, тренди, формати жартів. **Найдинамічніша частина** — меми живуть від днів до тижнів.

```json
{
  "id": "meme_001",
  "title": "ну шо, помолімось",
  "format": "text_phrase",
  "description": "використовується перед чимось складним або безнадійним",
  "example": "завтра дедлайн, ну шо, помолімось",
  "template": "{контекст}, ну шо, помолімось",
  "first_seen": "2026-04-10",
  "last_seen": "2026-04-24",
  "peak_date": "2026-04-18",
  "frequency_7d": 89,
  "frequency_trend": "declining",
  "lifecycle_stage": "past_peak",
  "virality_score": 7.2,
  "category": "reaction",
  "tags": ["текстовий", "реакція", "гумор"],
  "status": "active",
  "related_memes": ["meme_042"]
}
```

**Особливості:**
- `format`: `text_phrase` | `image_macro` | `video_ref` | `hashtag` | `challenge`
- `lifecycle_stage`: `emerging` | `rising` | `peak` | `past_peak` | `dead`
- `virality_score`: 0-10, розраховується з frequency + швидкість росту
- `template` — шаблон для генерації контенту агентом
- Щоденне оновлення, агресивне видалення мертвих (але зберігаємо в архіві)

**Логіка lifecycle:**
- Перші 3 дні + ріст → `emerging`
- Ріст > 50% за добу → `rising`
- Максимальна частота → `peak`
- Спад > 30% від піку → `past_peak`
- `frequency_7d` = 0 → `dead` (переносимо в архів)

---

## Метадані пакету

Щоденний пакет, який пушиться:

```json
{
  "package_date": "2026-04-24",
  "version": "2026.04.24",
  "stats": {
    "total_streaks": 1247,
    "total_slang_active": 389,
    "total_slang_deprecated": 156,
    "total_memes_active": 42,
    "total_memes_archived": 891,
    "new_today": {
      "streaks": 3,
      "slang": 1,
      "memes": 5
    },
    "deprecated_today": {
      "slang": 2,
      "memes": 8
    }
  },
  "parsing_source": "threads",
  "parsing_accounts_count": 250,
  "parsing_posts_processed": 4800
}
```

---

## Структура файлів (план)

```
ua-slang-mcp/
├── README.md
├── DATASET_STRUCTURE.md          ← ти тут
├── pyproject.toml
├── src/
│   └── ua_slang_mcp/
│       ├── __init__.py
│       ├── server.py             # MCP сервер (HTTP + stdio)
│       ├── models.py             # Pydantic моделі
│       ├── tools/
│       │   ├── search.py         # пошук по всіх 3 напрямках
│       │   ├── trending.py       # що зараз trending
│       │   ├── suggest.py        # підказки для контенту
│       │   └── package.py        # отримати щоденний пакет
│       ├── parser/
│       │   ├── threads.py        # парсер Threads
│       │   ├── detector.py       # детекція нових слів/мемів
│       │   └── lifecycle.py      # трекінг lifecycle (тренди, спад)
│       ├── storage/
│       │   ├── db.py             # PostgreSQL
│       │   └── publisher.py      # щоденний пакет + пуш
│       └── config.py
├── data/
│   ├── streaks.json              # поточний стрік-словник
│   ├── slang.json                # поточний сленг-словник
│   ├── memes_active.json         # активні меми
│   ├── memes_archive/            # архів мертвих мемів
│   │   └── 2026-04.json
│   └── packages/                 # щоденні пакети
│       └── 2026-04-24.json
├── tests/
├── docker-compose.yml
├── Dockerfile
└── .github/
    └── workflows/
        └── daily-parse.yml       # GitHub Actions — щоденний парсинг
```

---

## MCP Tools (для AI-агентів)

| Tool | Опис |
|------|------|
| `search_slang` | Пошук сленгу за словом або значенням |
| `search_streaks` | Пошук стійких виразів |
| `get_trending_memes` | Топ мемів зараз (за virality_score) |
| `get_trending_slang` | Сленг, що росте (frequency_trend = rising) |
| `suggest_for_post` | Підказати сленг/мем для конкретної теми поста |
| `get_daily_package` | Отримати щоденний пакет оновлень |
| `check_freshness` | Перевірити чи слово/мем ще актуальне |
| `get_replacement` | Знайти заміну для застарілого сленгу |

---

## Наступні кроки

1. [ ] Почистити і привести до ладу цю структуру
2. [ ] Реалізувати парсер Threads
3. [ ] Детектор нових слів/мемів
4. [ ] Lifecycle трекінг (тренди, спад, архівація)
5. [ ] PostgreSQL моделі
6. [ ] MCP сервер (tools)
7. [ ] Щоденний pipeline (GitHub Actions)
8. [ ] Пакування і пуш щоденного пакету
