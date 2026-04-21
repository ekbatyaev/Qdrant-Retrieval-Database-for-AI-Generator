# task-repo

FastAPI-сервис для семантического поиска по двум типам данных:
- **документация по методам**;
- **примеры пользовательских запросов и ответов**.

В качестве векторной базы используется **Qdrant**, а для поиска и переоценки результатов — модели **Sentence Transformers**:
- `intfloat/multilingual-e5-large` — для эмбеддингов;
- `BAAI/bge-reranker-v2-m3` — для rerank.

Проект запускается в Docker через `docker-compose`: отдельно поднимается контейнер с API и контейнер с Qdrant. При старте приложения данные из JSON-файлов автоматически индексируются в коллекции Qdrant.

---

## Возможности

- индексация документации и примеров при запуске сервиса;
- семантический поиск по документации;
- семантический поиск по примерам запросов;
- rerank найденных результатов для повышения релевантности;
- добавление новых записей в документацию через API;
- добавление новых примеров через API;
- защита основных эндпоинтов через заголовок `token`;
- идемпотентная индексация: одинаковые записи не дублируются, а обновляются по стабильному `uuid`.

---

## Стек

- Python 3.12
- FastAPI
- Uvicorn
- Qdrant
- sentence-transformers
- qdrant-client
- python-dotenv
- Docker / Docker Compose

---

## Структура проекта

```text
task-repo/
├── app/
│   ├── data/                         # актуальные JSON-данные для индексации
│   ├── data_old/                     # старые версии данных
│   ├── example_request_to_fastapi.py # пример клиентских запросов к API
│   └── main.py                       # основной FastAPI-сервис
├── qdrant_storage/                   # локальное хранилище Qdrant
│   ├── aliases/
│   ├── collections/
│   └── raft_state.json
├── qdrant_storage_old/               # старая версия хранилища Qdrant
├── .env                              # переменные окружения
├── .gitignore
├── chat_with_model.py                # дополнительный скрипт взаимодействия с моделью
├── docker-compose.yml                # запуск API и Qdrant
├── Dockerfile                        # образ приложения
├── README.md
└── requirements.txt                  # Python-зависимости
```

---

## Как работает сервис

### 1. Загрузка конфигурации
Приложение читает настройки из `.env`:
- токен доступа;
- адрес Qdrant;
- названия коллекций;
- пути до JSON-файлов с данными;
- названия моделей;
- Hugging Face токен при необходимости.

### 2. Инициализация моделей
На старте загружаются:
- embedding-модель `intfloat/multilingual-e5-large`;
- reranker `BAAI/bge-reranker-v2-m3`.

### 3. Подключение к Qdrant
Если коллекции ещё не созданы, сервис создаёт их автоматически.

Используются две коллекции:
- `lua_documentation` — документация по методам;
- `lua_examples` — примеры запросов и ответов.

### 4. Индексация данных
Из файлов:
- `/app/data/documentation.json`
- `/app/data/examples.json`

читаются записи, для них строится `search_text`, затем создаются эмбеддинги и данные загружаются в Qdrant.

Для предотвращения дублей используется стабильный идентификатор записи:
- для документации — на основе `method_name`;
- для примеров — на основе `request_text`.

### 5. Поиск
При поиске:
1. запрос пользователя преобразуется в эмбеддинг;
2. выполняется поиск ближайших векторов в Qdrant;
3. результаты фильтруются по порогу `similarity`;
4. лучшие кандидаты дополнительно сортируются reranker-моделью;
5. API возвращает итоговый список документов.

---

## Формат данных

### Документация
Ожидается список объектов вида:

```json
[
  {
    "method_name": "player.addItem",
    "method_description": "Добавляет указанный предмет в инвентарь игрока",
    "method_realization": "function ... end"
  }
]
```

### Примеры
Ожидается список объектов вида:

```json
[
  {
    "request_text": "Как выдать игроку 5 зелий лечения после завершения квеста?",
    "request_data_example": "{ ... }",
    "request_answer_example": "local player = ..."
  }
]
```

---

## API эндпоинты

### `GET /`
Проверка работоспособности сервиса.

**Ответ:**
```json
{
  "status": "ok",
  "vector_db": "qdrant"
}
```

---

### `POST /documentation_search`
Семантический поиск по документации.

**Заголовки:**
```http
token: <YOUR_TOKEN>
```

**Тело запроса:**
```json
{
  "query": "как добавить предмет игроку",
  "similarity": 0.35,
  "count_doc_return": 10,
  "count_doc_rerank": 25
}
```

**Поля:**
- `query` — текст запроса;
- `similarity` — минимальный порог схожести;
- `count_doc_return` — сколько документов вернуть;
- `count_doc_rerank` — сколько документов отправить на rerank.

**Ответ:**
```json
[
  {
    "method_name": "player.addItem",
    "method_description": "Добавляет указанный предмет в инвентарь игрока",
    "method_realization": "function ... end",
    "score": 0.82,
    "rerank_score": 0.96
  }
]
```

---

### `POST /examples_search`
Семантический поиск по примерам запросов.

**Заголовки:**
```http
token: <YOUR_TOKEN>
```

**Тело запроса:**
```json
{
  "query": "как выдать награду после квеста",
  "similarity": 0.35,
  "count_doc_return": 10,
  "count_doc_rerank": 25
}
```

**Ответ:**
```json
[
  {
    "request_text": "Как выдать игроку 5 зелий лечения после завершения квеста?",
    "request_data_example": "{ ... }",
    "request_answer_example": "local player = ...",
    "score": 0.79,
    "rerank_score": 0.91
  }
]
```

---

### `POST /documentation_add`
Добавление или обновление записи документации.

**Заголовки:**
```http
token: <YOUR_TOKEN>
```

**Тело запроса:**
```json
{
  "method_name": "player.addItem",
  "method_description": "Добавляет указанный предмет в инвентарь игрока по item_id и quantity.",
  "method_realization": "function rewardPlayer(player, item_id, quantity) ... end"
}
```

**Ответ:**
```json
{
  "method_name": "player.addItem",
  "method_added_or_updated": true
}
```

---

### `POST /examples_add`
Добавление или обновление примера.

**Заголовки:**
```http
token: <YOUR_TOKEN>
```

**Тело запроса:**
```json
{
  "request_text": "Как выдать игроку 5 зелий лечения после завершения квеста?",
  "request_data_example": "{ ... }",
  "request_answer_example": "local player = ..."
}
```

**Ответ:**
```json
{
  "request_text": "Как выдать игроку 5 зелий лечения после завершения квеста?",
  "request_added_or_updated": true
}
```

---

## Локальный запуск без Docker

### 1. Установить зависимости
```bash
pip install -r requirements.txt
```

### 2. Поднять Qdrant
Можно запустить отдельно в Docker:

```bash
docker run -p 6333:6333 qdrant/qdrant
```

### 3. Подготовить `.env`
Пример:

```env
TOKEN=your_secret_token
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_TIMEOUT=90

DOCUMENTATION_COLLECTION=lua_documentation
EXAMPLES_COLLECTION=lua_examples

EMBEDDING_MODEL_NAME=intfloat/multilingual-e5-large
RERANKER_MODEL_NAME=BAAI/bge-reranker-v2-m3

DOCUMENTATION_DATA_PATH=/app/data/documentation.json
EXAMPLES_DATA_PATH=/app/data/examples.json

HF_TOKEN=your_huggingface_token
DATABASE_API_BASE_URL=http://localhost:8001
```

### 4. Запустить приложение
Из папки `app`:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Либо:

```bash
python main.py
```

---

## Запуск через Docker Compose

```bash
docker-compose up --build
```

После запуска будут доступны:
- API: `http://localhost:8001`
- Qdrant: `http://localhost:6333`

> В `docker-compose.yml` приложение публикуется наружу как `8001:8000`, а Qdrant — как `127.0.0.1:6333:6333`.

---

## Dockerfile

Логика сборки образа:
1. используется `python:3.12-slim`;
2. устанавливаются зависимости из `requirements.txt`;
3. содержимое папки `app/` копируется в `/app/`;
4. приложение запускается через Uvicorn на порту `8000`.

---

## Пример клиентского запроса

В репозитории есть файл `app/example_request_to_fastapi.py`, который показывает, как:
- выполнить healthcheck;
- искать по документации;
- искать по примерам;
- добавлять новые записи в обе коллекции.

Пример запуска:

```bash
python app/example_request_to_fastapi.py
```

Скрипт использует:
- `DATABASE_API_BASE_URL`
- `TOKEN`

из файла `.env`.

---

## Переменные окружения

| Переменная | Описание |
|---|---|
| `TOKEN` | токен для доступа к защищённым эндпоинтам |
| `DATABASE_API_BASE_URL` | базовый URL API для клиентского скрипта |
| `QDRANT_URL` | адрес Qdrant |
| `QDRANT_API_KEY` | API-ключ Qdrant, если используется |
| `QDRANT_TIMEOUT` | таймаут запросов к Qdrant |
| `DOCUMENTATION_COLLECTION` | имя коллекции документации |
| `EXAMPLES_COLLECTION` | имя коллекции примеров |
| `EMBEDDING_MODEL_NAME` | модель для генерации эмбеддингов |
| `RERANKER_MODEL_NAME` | модель для rerank |
| `DOCUMENTATION_DATA_PATH` | путь к JSON с документацией |
| `EXAMPLES_DATA_PATH` | путь к JSON с примерами |
| `HF_TOKEN` | токен Hugging Face для загрузки моделей |

---

## Зависимости

В проекте используются следующие основные библиотеки:
- `pandas`
- `sentence-transformers`
- `numpy`
- `fastapi`
- `uvicorn`
- `python-dotenv`
- `qdrant-client>=1.9.1`

---

## Особенности реализации

### Стабильные идентификаторы
Для каждой записи создаётся детерминированный `uuid5`, поэтому:
- одна и та же запись не вставляется повторно;
- при изменении содержимого запись обновляется;
- индекс остаётся консистентным между перезапусками.

### Что именно индексируется
Сейчас в `search_text` попадает только:
- для документации — `method_description`;
- для примеров — `request_text`.

Это делает поиск более сфокусированным, но при необходимости можно расширить индексируемый текст, добавив имя метода, реализацию, пример данных и ответ.

### Фильтрация результатов
После векторного поиска результаты:
- фильтруются по `similarity`;
- затем сортируются reranker-моделью;
- возвращаются в количестве `count_doc_return`.

---

## Что можно улучшить

- добавить Swagger-описания и примеры схем;
- вынести индексацию в отдельную команду или сервис;
- добавить удаление записей через API;
- добавить batch-загрузку документов;
- добавить логирование метрик поиска;
- покрыть проект тестами;
- скрыть локальные хранилища Qdrant из репозитория, если они не должны храниться в git;
- убрать реальные секреты из `.env` и хранить только шаблон `.env.example`.

---

## Рекомендации по безопасности

Сейчас в репозитории присутствует `.env`. Для публичного репозитория лучше:
1. удалить реальные токены и ключи;
2. добавить `.env` в `.gitignore`;
3. оставить только `.env.example` с шаблонными значениями.

Пример `.env.example`:

```env
TOKEN=your_secret_token
DATABASE_API_BASE_URL=http://localhost:8001
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=
QDRANT_TIMEOUT=90
DOCUMENTATION_COLLECTION=lua_documentation
EXAMPLES_COLLECTION=lua_examples
EMBEDDING_MODEL_NAME=intfloat/multilingual-e5-large
RERANKER_MODEL_NAME=BAAI/bge-reranker-v2-m3
DOCUMENTATION_DATA_PATH=/app/data/documentation.json
EXAMPLES_DATA_PATH=/app/data/examples.json
HF_TOKEN=your_huggingface_token
```

---

## Кратко

Этот репозиторий — готовый API-сервис для семантического поиска по JSON-данным с использованием Qdrant и моделей Sentence Transformers. Он подходит для поиска по внутренней документации, примерам кода, подсказкам для генерации Lua-логики и похожим задачам, где нужен быстрый релевантный поиск по текстовым записям.
