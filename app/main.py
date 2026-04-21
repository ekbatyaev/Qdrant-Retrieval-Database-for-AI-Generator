import json
import logging
import os
import sys
import traceback
import uuid
from typing import Any, Callable, Dict, List, Optional, Tuple

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import CrossEncoder, SentenceTransformer


load_dotenv()

TOKEN = os.getenv("TOKEN", "")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

EXAMPLES_COLLECTION = os.getenv("EXAMPLES_COLLECTION", "lua_examples")
DOCUMENTATION_COLLECTION = os.getenv("DOCUMENTATION_COLLECTION", "lua_documentation")

EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "intfloat/multilingual-e5-large")
RERANKER_MODEL_NAME = os.getenv("RERANKER_MODEL_NAME", "BAAI/bge-reranker-v2-m3")
HF_TOKEN = os.getenv("HF_TOKEN")

DOCUMENTATION_DATA_PATH = os.getenv("DOCUMENTATION_DATA_PATH", "/app/data/documentation.json")
EXAMPLES_DATA_PATH = os.getenv("EXAMPLES_DATA_PATH", "/app/data/examples.json")

QDRANT_TIMEOUT = int(os.getenv("QDRANT_TIMEOUT", "60"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout,
    force=True,
)

logger = logging.getLogger(__name__)

app = FastAPI(title="Lua semantic search API (Qdrant)")

model: Optional[SentenceTransformer] = None
reranker: Optional[CrossEncoder] = None
qdrant_client: Optional[QdrantClient] = None
embedding_dim: Optional[int] = None
hf_auth_prepared = False


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    similarity: Optional[float] = 0.35
    count_doc_return: Optional[int] = 10
    count_doc_rerank: Optional[int] = 25


class DocumentationAddRequest(BaseModel):
    method_name: str
    method_description: str
    method_realization: str


class ExamplesAddRequest(BaseModel):
    request_text: str
    request_data_example: str
    request_answer_example: str
    request_algorithm: str


def load_data(path: str) -> List[Dict[str, Any]]:
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, list):
            raise ValueError(f"File {path} must contain a JSON array")

        logger.info("Файл %s загружен, записей: %d", path, len(data))
        return data

    except FileNotFoundError:
        logger.warning("Файл %s не найден, будет использован пустой список", path)
        return []
    except IsADirectoryError:
        logger.error("Путь %s указывает на директорию, а не на файл", path)
        return []
    except json.JSONDecodeError as exc:
        logger.error("Ошибка JSON в файле %s: %s", path, exc)
        return []
    except Exception as exc:
        logger.error("Ошибка чтения файла %s: %s", path, exc)
        logger.debug(traceback.format_exc())
        return []


def ensure_token(token: str) -> None:
    if token != TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")


def prepare_hf_auth() -> Dict[str, str]:
    global hf_auth_prepared

    if HF_TOKEN:
        os.environ["HF_TOKEN"] = HF_TOKEN
        os.environ["HUGGINGFACE_HUB_TOKEN"] = HF_TOKEN
        if not hf_auth_prepared:
            logger.info("Будет использован HF_TOKEN для загрузки моделей из Hugging Face")
            hf_auth_prepared = True
        return {"token": HF_TOKEN}

    if not hf_auth_prepared:
        logger.info("HF_TOKEN не задан, модели будут загружаться без авторизации")
        hf_auth_prepared = True

    return {}


def load_models() -> Tuple[SentenceTransformer, CrossEncoder, int]:
    global model, reranker, embedding_dim

    hf_kwargs = prepare_hf_auth()

    if model is None:
        logger.info("Загрузка embedding-модели: %s", EMBEDDING_MODEL_NAME)
        model = SentenceTransformer(EMBEDDING_MODEL_NAME, **hf_kwargs)
        embedding_dim = model.get_embedding_dimension()
        if embedding_dim is None:
            raise RuntimeError("Не удалось определить размерность embedding-модели")
        logger.info("Embedding-модель загружена. Размерность: %d", embedding_dim)

    if reranker is None:
        logger.info("Загрузка reranker-модели: %s", RERANKER_MODEL_NAME)
        reranker = CrossEncoder(RERANKER_MODEL_NAME, **hf_kwargs)
        logger.info("Reranker-модель загружена")

    return model, reranker, embedding_dim


def get_qdrant_client(token: str) -> QdrantClient:
    global qdrant_client
    ensure_token(token)

    if qdrant_client is None:
        logger.info("Подключение к Qdrant: %s", QDRANT_URL)
        qdrant_client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY or None,
            timeout=QDRANT_TIMEOUT,
        )
    return qdrant_client

def build_documentation_search_text(item: Dict[str, Any]) -> str:
    method_description = str(item.get("method_description") or "").strip()
    return method_description

def build_examples_search_text(item: Dict[str, Any]) -> str:
    request_text = str(item.get("request_text") or "").strip()
    return request_text

def make_stable_point_id(collection_name: str, item: Dict[str, Any]) -> str:
    if collection_name == DOCUMENTATION_COLLECTION:
        unique_key = str(item.get("method_name") or "").strip().lower()
    elif collection_name == EXAMPLES_COLLECTION:
        unique_key = str(item.get("request_text") or "").strip().lower()
    else:
        raw = json.dumps(item, ensure_ascii=False, sort_keys=True)
        unique_key = raw

    if not unique_key:
        raw = json.dumps(item, ensure_ascii=False, sort_keys=True)
        unique_key = raw

    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{collection_name}:{unique_key}"))


def get_existing_point(
    client: QdrantClient,
    collection_name: str,
    point_id: str,
) -> Optional[Any]:
    result = client.retrieve(
        collection_name=collection_name,
        ids=[point_id],
        with_payload=True,
        with_vectors=False,
    )
    if not result:
        return None
    return result[0]


def normalize_payload_for_compare(payload: Dict[str, Any]) -> Dict[str, Any]:
    return dict(payload)


def get_embedding(text: str) -> List[float]:
    current_model, _, _ = load_models()
    vector = current_model.encode(
        text,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return vector.tolist()


def ensure_collection(client: QdrantClient, collection_name: str) -> None:
    _, _, dim = load_models()

    if client.collection_exists(collection_name=collection_name):
        logger.info("Коллекция %s уже существует", collection_name)
        return

    logger.info("Создание коллекции %s", collection_name)
    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
    )


def collection_count(client: QdrantClient, collection_name: str) -> int:
    if not client.collection_exists(collection_name=collection_name):
        return 0
    return client.count(collection_name=collection_name, exact=True).count


def upsert_records(
    client: QdrantClient,
    *,
    collection_name: str,
    items: List[Dict[str, Any]],
    search_text_builder: Callable[[Dict[str, Any]], str],
) -> int:
    if not items:
        logger.warning("Для коллекции %s нет данных для индексации", collection_name)
        return 0

    points: List[models.PointStruct] = []
    skipped_empty = 0
    skipped_unchanged = 0
    created_or_updated = 0
    total = len(items)

    for index, item in enumerate(items, start=1):
        payload = dict(item)
        payload["search_text"] = search_text_builder(item)

        item_name = (
            item.get("request_text")
            or item.get("method_name")
            or f"record_{index}"
        )

        logger.info(
            "[%s] Обработка записи %d/%d: %s",
            collection_name,
            index,
            total,
            str(item_name)[:200],
        )

        if not payload["search_text"].strip():
            skipped_empty += 1
            logger.warning(
                "[%s] Запись %d/%d пропущена: пустой search_text",
                collection_name,
                index,
                total,
            )
            continue

        point_id = make_stable_point_id(collection_name, item)
        existing_point = get_existing_point(client, collection_name, point_id)

        if existing_point is not None:
            existing_payload = dict(existing_point.payload or {})

            if normalize_payload_for_compare(existing_payload) == normalize_payload_for_compare(payload):
                skipped_unchanged += 1
                logger.info(
                    "[%s] Запись %d/%d не изменилась, пропуск: %s",
                    collection_name,
                    index,
                    total,
                    str(item_name)[:200],
                )
                continue

            logger.info(
                "[%s] Запись %d/%d изменена, будет обновлена: %s",
                collection_name,
                index,
                total,
                str(item_name)[:200],
            )
        else:
            logger.info(
                "[%s] Новая запись %d/%d, будет добавлена: %s",
                collection_name,
                index,
                total,
                str(item_name)[:200],
            )

        vector = get_embedding(payload["search_text"])
        points.append(
            models.PointStruct(
                id=point_id,
                vector=vector,
                payload=payload,
            )
        )
        created_or_updated += 1

    if not points:
        logger.warning(
            "Для коллекции %s не сформировано ни одной новой/обновлённой точки. "
            "Пропущено пустых: %d, без изменений: %d",
            collection_name,
            skipped_empty,
            skipped_unchanged,
        )
        return 0

    logger.info(
        "Отправка %d точек в коллекцию %s. "
        "Пропущено пустых: %d, без изменений: %d",
        len(points),
        collection_name,
        skipped_empty,
        skipped_unchanged,
    )

    client.upsert(collection_name=collection_name, points=points, wait=True)

    logger.info(
        "Индексация коллекции %s завершена. Добавлено/обновлено: %d",
        collection_name,
        created_or_updated,
    )
    return created_or_updated


def rerank_results(query: str, rows: List[Dict[str, Any]], field_name: str) -> List[Dict[str, Any]]:
    _, current_reranker, _ = load_models()

    if not rows:
        return rows

    pairs = [(query, str(row.get(field_name, ""))) for row in rows]
    scores = current_reranker.predict(pairs)

    for row, score in zip(rows, scores):
        row["rerank_score"] = round(float(score), 6)

    rows.sort(
        key=lambda x: (x.get("rerank_score", 0.0), x.get("score", 0.0)),
        reverse=True,
    )
    return rows


def search_collection(
    client: QdrantClient,
    *,
    collection_name: str,
    query: str,
    similarity: float,
    count_doc_return: int,
    count_doc_rerank: int,
    rerank_field: str,
    response_fields: List[str],
) -> List[Dict[str, Any]]:
    limit = max(count_doc_rerank * 3, count_doc_return)
    query_vector = get_embedding(query)

    result = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )

    hits = result.points or []

    rows: List[Dict[str, Any]] = []
    for hit in hits:
        score = float(hit.score)
        if score < similarity:
            continue

        payload = hit.payload or {}
        row = {field: payload.get(field, "") for field in response_fields}
        row["score"] = round(score, 6)
        rows.append(row)

    rows = rerank_results(query, rows[:count_doc_rerank], rerank_field)
    return rows[:count_doc_return]


@app.on_event("startup")
def startup() -> None:
    try:
        logger.info("Инициализация приложения...")
        load_models()
        client = get_qdrant_client(TOKEN)

        ensure_collection(client, DOCUMENTATION_COLLECTION)
        ensure_collection(client, EXAMPLES_COLLECTION)

        documentation_before = collection_count(client, DOCUMENTATION_COLLECTION)
        examples_before = collection_count(client, EXAMPLES_COLLECTION)

        logger.info(
            "До индексации в Qdrant: documentation=%d, examples=%d",
            documentation_before,
            examples_before,
        )

        documentation_items = load_data(DOCUMENTATION_DATA_PATH)
        examples_items = load_data(EXAMPLES_DATA_PATH)

        documentation_indexed = upsert_records(
            client,
            collection_name=DOCUMENTATION_COLLECTION,
            items=documentation_items,
            search_text_builder=build_documentation_search_text,
        )
        examples_indexed = upsert_records(
            client,
            collection_name=EXAMPLES_COLLECTION,
            items=examples_items,
            search_text_builder=build_examples_search_text,
        )

        documentation_after = collection_count(client, DOCUMENTATION_COLLECTION)
        examples_after = collection_count(client, EXAMPLES_COLLECTION)

        logger.info(
            "Инициализация завершена. Добавлено/обновлено сейчас: documentation=%s, examples=%s. "
            "В Qdrant после запуска: documentation=%s, examples=%s",
            documentation_indexed,
            examples_indexed,
            documentation_after,
            examples_after,
        )
    except Exception as exc:
        logger.error("Фатальная ошибка инициализации: %s", exc)
        logger.debug(traceback.format_exc())
        raise RuntimeError("Application initialization failed") from exc


@app.post("/documentation_search")
def documentation_search(req: SearchRequest, token: str = Header(...)):
    try:
        client = get_qdrant_client(token)
        return search_collection(
            client,
            collection_name=DOCUMENTATION_COLLECTION,
            query=req.query,
            similarity=float(req.similarity or 0.0),
            count_doc_return=int(req.count_doc_return or 10),
            count_doc_rerank=int(req.count_doc_rerank or 25),
            rerank_field="method_description",
            response_fields=["method_name", "method_description", "method_realization"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Ошибка поиска по documentation: %s", exc)
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/examples_search")
def examples_search(req: SearchRequest, token: str = Header(...)):
    try:
        client = get_qdrant_client(token)
        return search_collection(
            client,
            collection_name=EXAMPLES_COLLECTION,
            query=req.query,
            similarity=float(req.similarity or 0.0),
            count_doc_return=int(req.count_doc_return or 10),
            count_doc_rerank=int(req.count_doc_rerank or 25),
            rerank_field="request_text",
            response_fields=["request_text", "request_data_example", "request_answer_example", "request_algorithm"],
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Ошибка поиска по examples: %s", exc)
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/documentation_add")
def documentation_add(req: DocumentationAddRequest, token: str = Header(...)):
    try:
        client = get_qdrant_client(token)
        indexed = upsert_records(
            client,
            collection_name=DOCUMENTATION_COLLECTION,
            items=[req.model_dump()],
            search_text_builder=build_documentation_search_text,
        )
        return {
            "method_name": req.method_name,
            "method_added_or_updated": bool(indexed),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Ошибка добавления метода %s: %s", req.method_name, exc)
        logger.debug(traceback.format_exc())
        return {
            "method_name": req.method_name,
            "method_added_or_updated": False,
        }


@app.post("/examples_add")
def examples_add(req: ExamplesAddRequest, token: str = Header(...)):
    try:
        client = get_qdrant_client(token)
        indexed = upsert_records(
            client,
            collection_name=EXAMPLES_COLLECTION,
            items=[req.model_dump()],
            search_text_builder=build_examples_search_text,
        )
        return {
            "request_text": req.request_text,
            "request_added_or_updated": bool(indexed),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Ошибка добавления примера %s: %s", req.request_text, exc)
        logger.debug(traceback.format_exc())
        return {
            "request_text": req.request_text,
            "request_added_or_updated": False,
        }


@app.get("/")
def health():
    return {"status": "ok", "vector_db": "qdrant"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)