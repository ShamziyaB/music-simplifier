# Music Simplifier

Веб-приложение, которое упрощает ноты в формате MusicXML для начинающих.
Загрузите файл, выберите уровень сложности и получите упрощённые ноты,
MIDI для прослушивания и отчёт о том, что изменилось.

> **Важно.** Приложение предназначено только для личного учебного использования.
> Не распространяйте ноты, защищённые авторским правом, без разрешения
> правообладателя. Упрощение — это помощь, а не замена преподавателю: результат
> всегда нужно проверять на слух и глазами.

## Что уже работает

- Загрузка `.musicxml`, `.xml`, `.mxl` (до 3 МБ).
- Три уровня упрощения:
  - **Легко** — аккорды сводятся к трезвучиям, удвоения убираются.
  - **Средне** — аккорд может сохранить четвёртый звук, удвоения убираются.
  - **Средне-сложно** — минимальные правки, удвоения сохраняются.
- Перенос нот в удобный диапазон руки.
- Предпросмотр нот в браузере через OpenSheetMusicDisplay.
- Скачивание MusicXML, MIDI и текстового отчёта.
- Проверка результата: размер, число тактов и нот, диапазон, тональность.
- Тёмный адаптивный интерфейс на русском языке.

PDF, фото и распознавание нот (OMR) пока не поддерживаются. Если у вас PDF,
экспортируйте MusicXML из MuseScore: **Файл → Экспорт → MusicXML**.

## Стек

```text
web/                    Next.js 16 + React 19 + OpenSheetMusicDisplay  → Vercel
app.py                  FastAPI                                        → Vercel Python
simplifier/             music21, правила упрощения и проверки
Dockerfile, render.yaml запасной вариант запуска API на Render
tests/                  pytest: правила, конвейер, HTTP API
```

`web/` и Python-API — два проекта Vercel из одного репозитория. Браузер
отправляет MusicXML на API, получает упрощённый файл и отчёт. Файлы не
сохраняются на сервере: обработка идёт во временной папке.

## Локальный запуск

Нужны Python 3.11+ и Node.js 20+.

### 1. Бэкенд

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements-dev.txt
uvicorn app:app --reload --port 8000
```

API будет доступен на `http://localhost:8000`, документация — на
`http://localhost:8000/docs`.

### 2. Фронтенд

В отдельном терминале:

```bash
cd web
npm install
npm run dev
```

Откройте `http://localhost:3000`. По умолчанию фронтенд обращается к
`http://localhost:8000`. Адрес можно изменить в `web/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Тесты и сборка

```bash
# из корня проекта
pytest -q

# из web/
npm run typecheck
npm run build
```

### CLI

Правила можно запускать и без сайта:

```bash
python -m simplifier samples/piano_sample.musicxml --level easy --midi
python -m simplifier samples/piano_sample.musicxml --level medium
python -m simplifier samples/piano_sample.musicxml --level medium_hard
```

Результат появится рядом с исходным файлом: MusicXML, отчёт и, с флагом
`--midi`, MIDI.

## Деплой на Vercel

Оба проекта деплоятся из одного GitHub-репозитория.

### API

1. В Vercel: **New Project → Import Git Repository**.
2. Root Directory оставьте корнем репозитория.
3. Vercel сам определит FastAPI по `app.py` и `requirements.txt`.
4. Framework Preset: **FastAPI** (если спросит).
5. Deploy. Адрес будет вида `https://music-simplifier-api.vercel.app`.
6. Проверьте `https://music-simplifier-api.vercel.app/api/health`.

В `vercel.json` уже заданы `maxDuration` и исключение лишних файлов из
Python-бандла. Лимит функции — 500 МБ, проект в него укладывается.

### Сайт

1. В Vercel: **New Project → Import Git Repository** (тот же репозиторий).
2. **Root Directory:** `web`.
3. **Framework Preset:** Next.js.
4. В **Environment Variables** добавьте:
   ```text
   NEXT_PUBLIC_API_URL=https://music-simplifier-api.vercel.app
   ```
5. Deploy. После изменения переменной окружения нужен redeploy, потому что
   `NEXT_PUBLIC_*` встраивается в сборку.

CORS уже разрешает `http://localhost:3000` и домены `*.vercel.app`. Если
подключаете свой домен, добавьте его в переменную `ALLOWED_ORIGINS` проекта API
(через запятую) и сделайте redeploy.

### Запасной вариант: Render

Если Vercel-функция не подходит по размеру/времени, API можно запустить на
Render в Docker:

1. **New → Web Service →** подключите репозиторий.
2. Root Directory: корень репозитория.
3. Runtime: **Docker**.
4. Health Check Path: `/api/health`.
5. Переменные:
   - `ALLOWED_ORIGINS=https://ваш-сайт.vercel.app`
   - `MAX_FILE_BYTES=8388608` (если нужны файлы больше 3 МБ)
6. После деплоя укажите адрес Render в `NEXT_PUBLIC_API_URL` на Vercel.

`render.yaml` позволяет развернуть сервис через Blueprint. На бесплатном
тарифе Render сервис засыпает после простоя, поэтому первый запрос может быть
медленным.

## API

`POST /api/simplify`

```json
{
  "filename": "song.musicxml",
  "level": "easy",
  "content_base64": "<содержимое файла в base64>"
}
```

Ответ:

```json
{
  "filename": "song.musicxml",
  "level": "easy",
  "level_label": "Легко",
  "musicxml": "<упрощённый MusicXML>",
  "midi_base64": "<MIDI в base64 или null>",
  "report": "<текстовый отчёт>",
  "info": { "key": "C major", "time_signature": "4/4", "tempo_bpm": null, "parts": [] },
  "validation": { "ok": true, "errors": [], "warnings": [] },
  "stats": {
    "changes": 12,
    "chord_reductions": 2,
    "range_shifts": 10,
    "parts": 2,
    "note_events_before": 17,
    "note_events_after": 17
  }
}
```

Другие эндпоинты:

- `GET /api/health` — проверка работоспособности.
- `GET /api/levels` — список уровней.
- `GET /docs` — интерактивная документация FastAPI.

Максимальный размер файла по умолчанию — 3 МБ (ограничение Vercel на тело
запроса). На Render или локально его можно увеличить переменной
`MAX_FILE_BYTES` (в байтах).

## Ограничения и следующие шаги

- Упрощается ритм? Пока нет: сначала безопасные правила для аккордов и
  диапазона. Упрощение ритма, синкоп и триолей — следующий этап.
- Разделение мелодии и аккомпанемента, транспозиция в удобную тональность —
  следующие этапы.
- PDF/фото требуют OMR (Audiveris/Oemer) — это отдельный тяжёлый сервис,
  его лучше добавлять после веб-версии.
- Результат всегда проверяйте в MuseScore и на слух.

## Структура

```text
app.py                  FastAPI-приложение
simplifier/
  parser.py             чтение MusicXML
  analysis.py           тональность, размер, темп, диапазоны
  levels.py             настройки уровней
  simplify.py           правила упрощения
  validate.py           проверка результата
  report.py             текстовый отчёт
  service.py            обработка файла без HTTP
  export.py             сохранение MusicXML / MIDI / отчёта
  cli.py                командная строка
web/
  app/                  страница и стили Next.js
  components/           предпросмотр нот через OSMD
tests/                  pytest
samples/                тестовые MusicXML
Dockerfile              API для Render
render.yaml             Blueprint для Render
vercel.json             настройки Python-функции Vercel
```
