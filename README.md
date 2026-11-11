# Динамическое ценообразование авиабилетов (блок «Разработка», Вариант С)

Веб-приложение: страница с формой + backend API (FastAPI) + авторизация/регистрация (SQLite + JWT) + интерактивный график распределения спроса (Chart.js).

## Использованные технологии и инструменты ИИ
- **ML-прогноз спроса:** библиотека **AutoGluon TimeSeries** (`TimeSeriesPredictor`), выбранная модель **DirectTabular**, квантильный прогноз 0.1–0.9 (см. блок «Искусственный интеллект», файл `ФИО_ml_demand_forecast.ipynb`). Источник данных для сервиса — `data/my_forecast.csv`, сгенерированный заданием 7 ноутбука.
- **Backend:** Python, FastAPI, Uvicorn, SQLite (встроенный `sqlite3`), PyJWT, Pandas.
- **Frontend:** HTML5, CSS3, Vanilla JavaScript, Chart.js.
- **Инструменты ИИ при разработке:** для проектирования архитектуры, генерации кода и отладки использовались LLM-ассистенты (Qwen, DeepSeek).

## Формула расчёта (совпадает с заданием 7 кейса)
`хотят = base_demand − price_sensitivity × (цена − base_price)`
`продано = min(мест, хотят)`
где `base_demand` — квантильный прогноз спроса при базовой цене из `my_forecast.csv`, `base_price` и `price_sensitivity` — из `routes.csv`.

## Структура проекта
- `backend/` — серверная часть (`main.py`, `requirements.txt`)
- `docs/` — клиентская часть (`login.html`, `index.html`, `style.css`, `app.js`)
- `data/` — CSV с прогнозом (`my_forecast.csv`) и параметрами маршрутов (`routes.csv`)

## Как запустить локально
1. `pip install -r backend/requirements.txt`
2. `cd backend && uvicorn main:app --host 0.0.0.0 --port 8000`
3. Открыть `http://127.0.0.1:8000` → вход `admin` / `123456`.

## Как задеплоено
Render.com (Web Service, free tier): Root Directory = `backend`, Build = `pip install -r requirements.txt`, Start = `uvicorn main:app --host 0.0.0.0 --port $PORT`. Бесплатный сервер засыпает после ~15 мин простоя; первый запрос будит его (до ~50 сек).

## Примечание
Хранилище пользователей на free-tier непостоянно: зарегистрированные юзеры исчезают после рестарта контейнера, предзаполненный `admin/123456` воссоздаётся при каждом старте. В продакшене заменить на постоянный том / PostgreSQL.