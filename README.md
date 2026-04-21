# Qdrant Retrieval Database for AI Generator

FastAPI-сервис для семантического поиска по двум типам данных в Qdrant:

- документация по методам;
- примеры пользовательских запросов и ответов.

Проект поднимает API и Qdrant в Docker, автоматически индексирует JSON-данные при старте и поддерживает поиск с дополнительным rerank для повышения релевантности.

## Что умеет сервис

- индексирует документацию и примеры при запуске приложения;
- выполняет семантический поиск по документации;
- выполняет семантический поиск по примерам пользовательских запросов;
- переоценивает найденные результаты с помощью reranker-модели;
- добавляет или обновляет записи через API;
- защищает основные эндпоинты через заголовок `token`;
- использует стабильные `uuid5`, чтобы не дублировать одинаковые записи при повторной индексации.

## Стек

- Python 3.12
- FastAPI
- Uvicorn
- Qdrant
- sentence-transformers
- qdrant-client
- python-dotenv
- Docker / Docker Compose

## Модели

В проекте используются две модели:

- `intfloat/multilingual-e5-large` — для генерации эмбеддингов;
- `BAAI/bge-reranker-v2-m3` — для rerank найденных результатов.

## Архитектура

Сервис работает по следующей схеме:

1. приложение загружает настройки из `.env`;
2. инициализирует embedding-модель и reranker;
3. подключается к Qdrant и при необходимости создаёт коллекции;
4. читает данные из JSON-файлов;
5. строит `search_text`, эмбеддинги и индексирует записи;
6. принимает поисковый запрос, получает кандидатов из Qdrant и пересортировывает их reranker-моделью.

## Структура проекта

```text
Qdrant-Retrieval-Database-for-AI-Generator/
├── app/
│   ├── data/                         # JSON-данные для индексации
│   ├── example_request_to_fastapi.py # пример запросов к API
│   └── main.py                       # основной FastAPI-сервис
├── qdrant_storage/                   # локальное хранилище Qdrant
├── Dockerfile
├── docker-compose.yml
├── LICENSE
├── README.md
└── requirements.txt
```

## Используемые коллекции

По умолчанию сервис работает с двумя коллекциями Qdrant:

- `lua_documentation` — документация по методам;
- `lua_examples` — примеры запросов и ответов.

## Формат входных данных

### Документация

Ожидается JSON-массив объектов такого вида:

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

Ожидается JSON-массив объектов такого вида:

```json
[
  {
    "request_text": "Как выдать игроку 5 зелий лечения после завершения квеста?",
    "request_data_example": "{ ... }",
    "request_answer_example": "local player = ...",
    "request_algorithm": "Пошаговое описание логики или алгоритма"
  }
]
```

## Переменные окружения

| Переменная | Описание |
|---|---|
| `TOKEN` | токен доступа к защищённым эндпоинтам |
| `DATABASE_API_BASE_URL` | базовый URL API для клиентского скрипта |
| `QDRANT_URL` | адрес Qdrant |
| `QDRANT_API_KEY` | API-ключ Qdrant, если используется |
| `QDRANT_TIMEOUT` | таймаут запросов к Qdrant |
| `DOCUMENTATION_COLLECTION` | имя коллекции документации |
| `EXAMPLES_COLLECTION` | имя коллекции примеров |
| `EMBEDDING_MODEL_NAME` | модель для генерации эмбеддингов |
| `RERANKER_MODEL_NAME` | модель для rerank |
| `DOCUMENTATION_DATA_PATH` | путь к JSON-файлу с документацией |
| `EXAMPLES_DATA_PATH` | путь к JSON-файлу с примерами |
| `HF_TOKEN` | токен Hugging Face для загрузки моделей |

### Пример `.env`

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

## Запуск через Docker Compose

```bash
docker-compose up --build
```

После запуска будут доступны:

- API: `http://localhost:8001`
- Qdrant: `http://127.0.0.1:6333`

### Что делает Docker-конфигурация

- контейнер `app` запускает FastAPI-сервис;
- контейнер `qdrant` поднимает векторную базу;
- локальная папка `qdrant_storage` монтируется как хранилище Qdrant;
- переменные окружения подхватываются из файла `.env`.

## Локальный запуск без Docker

### 1. Установить зависимости

```bash
pip install -r requirements.txt
```

### 2. Запустить Qdrant

Например, так:

```bash
docker run -p 6333:6333 qdrant/qdrant
```

### 3. Подготовить `.env`

Убедитесь, что в `.env` указан корректный адрес Qdrant и пути к JSON-файлам.

### 4. Запустить API

Из папки `app`:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

или:

```bash
python main.py
```

## API

### `GET /`

Проверка работоспособности сервиса.

Пример ответа:

```json
{
  "status": "ok",
  "vector_db": "qdrant"
}
```

### `POST /documentation_search`

Семантический поиск по документации.

Заголовки:

```http
token: <YOUR_TOKEN>
```

Тело запроса:

```json
{
  "query": "как добавить предмет игроку",
  "similarity": 0.35,
  "count_doc_return": 10,
  "count_doc_rerank": 25
}
```

Пример ответа:

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

### `POST /examples_search`

Семантический поиск по примерам запросов.

Заголовки:

```http
token: <YOUR_TOKEN>
```

Тело запроса:

```json
{
  "query": "как выдать награду после квеста",
  "similarity": 0.35,
  "count_doc_return": 10,
  "count_doc_rerank": 25
}
```

Пример ответа:

```json
[
  {
    "request_text": "Как выдать игроку 5 зелий лечения после завершения квеста?",
    "request_data_example": "{ ... }",
    "request_answer_example": "local player = ...",
    "request_algorithm": "Пошаговое описание логики или алгоритма",
    "score": 0.79,
    "rerank_score": 0.91
  }
]
```

### `POST /documentation_add`

Добавляет или обновляет запись документации.

```json
{
  "method_name": "player.addItem",
  "method_description": "Добавляет указанный предмет в инвентарь игрока по item_id и quantity.",
  "method_realization": "function rewardPlayer(player, item_id, quantity) ... end"
}
```

Пример ответа:

```json
{
  "method_name": "player.addItem",
  "method_added_or_updated": true
}
```

### `POST /examples_add`

Добавляет или обновляет пример.

```json
{
  "request_text": "Как выдать игроку 5 зелий лечения после завершения квеста?",
  "request_data_example": "{ ... }",
  "request_answer_example": "local player = ...",
  "request_algorithm": "Пошаговое описание логики или алгоритма"
}
```

Пример ответа:

```json
{
  "request_text": "Как выдать игроку 5 зелий лечения после завершения квеста?",
  "request_added_or_updated": true
}
```

## Как устроен поиск

1. пользовательский запрос преобразуется в эмбеддинг;
2. сервис ищет ближайшие векторы в Qdrant;
3. результаты фильтруются по порогу `similarity`;
4. лучшие кандидаты дополнительно пересортировываются reranker-моделью;
5. API возвращает финальный список результатов.

## Особенности реализации

### Идемпотентная индексация

Для каждой записи создаётся стабильный `uuid5`:

- одинаковые записи не дублируются;
- изменённые записи обновляются;
- индекс остаётся консистентным между перезапусками.

### Что индексируется

Сейчас в `search_text` попадает:

- для документации — `method_description`;
- для примеров — `request_text`.

Это делает поиск более сфокусированным. При необходимости можно расширить индексируемый текст, добавив имя метода, реализацию, пример данных или ответ.

## Пример клиентского скрипта

В репозитории есть файл `app/example_request_to_fastapi.py`, который показывает, как:

- проверить доступность сервиса;
- выполнять поиск по документации;
- выполнять поиск по примерам;
- отправлять запросы на добавление новых записей.

Запуск:

```bash
python app/example_request_to_fastapi.py
```

## Что стоит улучшить дальше

- добавить `/.env.example` вместо хранения реального `.env` в репозитории;
- описать схемы запросов и ответов через OpenAPI/Swagger более подробно;
- вынести массовую индексацию в отдельную команду;
- добавить удаление записей через API;
- добавить batch-загрузку документов;
- покрыть проект тестами;
- добавить логирование и метрики качества поиска.

## Безопасность

Для публичного репозитория рекомендуется:

1. не хранить реальные токены и ключи в `.env`;
2. добавить `.env` в `.gitignore`;
3. оставить в репозитории только `.env.example` с шаблонными значениями.

## License

MIT
