# ML service: классификация отзывов

Сервис на **FastAPI**: регистрация и JWT, кошелёк с кредитами, асинхронные задачи предсказания (**Celery** + **Redis**), списание кредитов после успешного инференса, уровни лояльности (скидка к стоимости предикта), **PostgreSQL**, метрики **Prometheus** и дашборды **Grafana**. Есть клиент на **Streamlit** (запускается отдельно от compose).

## Задача и поток запроса

**Предметная область** — разбор **текста отзыва** (например, на русском или английском в зависимости от выбранной модели): пользователь передаёт строку и идентификатор модели, сервис **ставит задачу в очередь**, воркер считает предсказание и сохраняет результат (метка, уверенность и служебные поля). Пока задача в работе, HTTP API не блокируется: клиент опрашивает `GET /predictions/{id}` или использует Streamlit.

**Ограничение по объёму текста** задаётся `MAX_REVIEW_CHARS` (см. `.env.example`).

## Каталог ML-моделей (после `seed_ml_models`)

В реестре (`GET /models`) после сида по умолчанию три записи. **Базовая стоимость** в кредитах — поле `cost_credits_base`; фактическое списание может быть ниже из‑за лояльности (следующий раздел).

| Имя в БД | Тип (`model_type`) | Смысл | Базовая цена (кредиты) |
|----------|---------------------|--------|-------------------------|
| `tfidf_svm_en_sentiment` | `sklearn_tfidf` | **Английский** сентимент: TF‑IDF + линейный SVM; артефакты с Hugging Face Hub ([DineshKumar1329/Sentiment_Analysis](https://huggingface.co/DineshKumar1329/Sentiment_Analysis)) — два `joblib` (векторизатор + классификатор). | **1** |
| `rubert_tiny2_ru_financial_sentiment` | `embeddings_sklearn`* | **Русский**, домен **финансов**: RuBERT‑tiny2, классы *neutral / positive / negative* ([mxlcw/rubert-tiny2-russian-financial-sentiment](https://huggingface.co/mxlcw/rubert-tiny2-russian-financial-sentiment)). Инференс через Transformers (~29M параметров). | **2** |
| `rubert_tiny2_ru_sentiment` | `peft_lora`* | **Русский** **общий** сентимент (те же три класса; [seara/rubert-tiny2-russian-sentiment](https://huggingface.co/seara/rubert-tiny2-russian-sentiment)). Тип в БД `peft_lora`, на практике грузится как полная `AutoModelForSequenceClassification` с Hub. | **5** |

И здесь сначала вместо второй модели планировалось по логике брать бустинг, обученный на эмбеддингах, но оказывается на ХФ такого материала нет. 

\*Для типов `embeddings_sklearn` и `peft_lora` в `app/ml/dispatch.py` сейчас используется один и тот же HF‑бэкенд (`predict_peft_lora`): это **полные веса** с карточки модели, не отдельный PEFT‑адаптер.

Если у записи **пустой** `storage_path`, для `sklearn_tfidf` используется **заглушка** (`predict_stub`) — удобно для тестов.

Локальный sklearn‑пайплайн (один файл `joblib`) задаётся абсолютным путём в `storage_path`, например под `/data/models/...` в Docker — см. `app/ml/backend_sklearn.py`.

## Цены, кошелёк и лояльность

- **Единица биллинга** — условные **кредиты** (`GET /wallet/me`).
- **Списание** — только после **успешного** предикта (`completed`): запись в ledger на **эффективную** стоимость. Ошибка инференса или нехватка кредитов в момент исполнения → `failed`, деньги не списываются.
- **Эффективная стоимость** вызова:  
  `effective = max(0, cost_credits_base * (100 - discount_percentage) // 100)`  
  скидка в процентах из активного **уровня лояльности** (`app/services/pricing_service.py`). Из‑за целочисленного деления при высокой скидке и малой базовой цене результат может стать **0** кредитов.

**Уровни** (после `python -m scripts.seed_loyalty`):

| Уровень | Порог (предиктов за месяц, логика сида) | Скидка |
|---------|----------------------------------------|--------|
| Bronze  | 0+                                     | 0%     |
| Silver  | 10+                                    | 5%     |
| Gold    | 50+                                    | 10%    |

Пересчёт — `app/services/loyalty_service.py` и Celery‑задача `recompute_loyalty_task` (см. Beat). Пороги и проценты хранятся в БД.

**Пополнение (демо):** `POST /billing/mock-topup` с `{"credits_to_add": N}`. Реального платёжного шлюза нет.

**Идемпотентность:** заголовок `Idempotency-Key` на `POST /predictions` — повтор с тем же ключом возвращает ту же задачу.

## Стек

- Python 3.12, FastAPI, SQLAlchemy, Alembic  
- Celery, Redis  
- scikit-learn / joblib, Hugging Face Transformers (опционально для моделей из Hub)  
- Docker Compose, Prometheus, Grafana  

## Быстрый старт (Docker)

Из корня проекта:

```bash
cp .env.example .env
# Укажите надёжный JWT_SECRET_KEY и при необходимости поправьте переменные.
docker compose up --build -d
```

Переменные из `.env` подхватываются сервисами `api`, `workers`, `beat`; URL БД для контейнеров переопределены в `docker-compose.yml` (Postgres внутри сети compose).

**Миграции БД** (после первого запуска):

```bash
docker compose exec api alembic upgrade head
```

**Начальные данные** (миграции должны быть применены; сиды не перезаписывают непустые таблицы):

```bash
docker compose exec api python -m scripts.seed_ml_models
docker compose exec api python -m scripts.seed_loyalty
```

### Сервисы и порты

| Сервис     | URL / порт |
|-----------|------------|
| API       | http://localhost:8000 |
| Swagger   | http://localhost:8000/docs |
| Postgres  | localhost:5432 (user/db: `mlservice`) |
| Redis     | localhost:6379 |
| Prometheus| http://localhost:9090 |
| Grafana   | http://localhost:3000 (логин по умолчанию `admin` / `admin`; только для локалки) |

Метрики приложения собираются с `http://api:8000/metrics` (конфиг в `prometheus/prometheus.yml`). В Grafana уже провайдятся datasource Prometheus и дашборд API (папка «ML Service»).

Том **`./data/models`** смонтирован в `api` и `workers` — сюда можно складывать локальные артефакты sklearn (`joblib`), если модель в БД ссылается на путь под `/data/models/...`.

## Переменные окружения

См. **`.env.example`**. Минимально нужны:

- `DATABASE_URL`, `REDIS_URL` — для локального запуска без compose; в compose для приложения задаются в `docker-compose.yml`.  
- `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`  
- `MODEL_STORAGE_PATH`, лимиты `MAX_REVIEW_CHARS`, `MAX_MODEL_UPLOAD_MB`, `ALLOWED_LORA_BASES`  
- для Celery: `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` (в compose заданы явно)  

Секреты и пароли в репозиторий не коммитить.

## Локальная разработка (без Docker)

1. PostgreSQL и Redis доступны локально, строки подключения в `.env`.  
2. `pip install -r requirements.txt`  
3. `alembic upgrade head`  
4. Сиды: `python -m scripts.seed_ml_models` и `python -m scripts.seed_loyalty`  
5. API: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`  
6. Worker: `celery -A app.celery_app worker -l info`  
7. Beat (лояльность): `celery -A app.celery_app beat -l info`  

## Streamlit

В **docker-compose** UI не поднят. Локально:

```bash
export ML_API_BASE=http://localhost:8000
streamlit run streamlit/app.py
```

Опционально задайте `API_BASE` в `.streamlit/secrets.toml`.

## Тесты

```bash
pip install -r requirements.txt
pytest tests/ -q
```

С покрытием (ориентир проекта — **>70%** по `app` и `core`):

```bash
pytest tests/ --cov=app --cov=core --cov-report=term-missing
```

## Артефакты в репозитории

- `app/` — API, сервисы, ML-диспетчеризация  
- `alembic/` — миграции  
- `prometheus/`, `grafana/` — мониторинг  
- `streamlit/` — веб-клиент  
- `scripts/` — `seed_ml_models`, `seed_loyalty` и прочие вспомогательные скрипты  

## Документация API

Интерактивно: **http://localhost:8000/docs** (OpenAPI).

---

Поле **роли** пользователя в модели предусмотрено; отдельная политика доступа по ролям может добавляться по мере необходимости.
