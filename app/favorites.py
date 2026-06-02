from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient

from app.config import MONGO_DB_NAME, MONGO_URL


client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=3000)
database = client[MONGO_DB_NAME]
collection = database["favorite_articles"]


def article_key(article: dict[str, Any]) -> str:
    source = article.get("originallink") or article.get("link") or article.get("title", "")
    return sha256(source.encode("utf-8")).hexdigest()


def normalize_article(article: Any) -> dict[str, Any]:
    if is_dataclass(article):
        data = asdict(article)
    else:
        data = dict(article)

    normalized = {
        "title": data.get("title", ""),
        "originallink": data.get("originallink", ""),
        "link": data.get("link", ""),
        "description": data.get("description", ""),
        "pub_date": data.get("pub_date", ""),
        "image_url": data.get("image_url", ""),
    }
    normalized["id"] = data.get("id") or article_key(normalized)
    normalized["is_favorite"] = True
    return normalized


def public_article(document: dict[str, Any]) -> dict[str, Any]:
    article = normalize_article(document)
    article["id"] = document.get("_id", article["id"])
    article["is_favorite"] = True
    return article


async def load_favorites() -> list[dict[str, Any]]:
    cursor = collection.find({}).sort("saved_at", -1)
    documents = await cursor.to_list(length=1000)
    return [public_article(document) for document in documents]


async def favorite_ids() -> set[str]:
    cursor = collection.find({}, {"_id": 1})
    documents = await cursor.to_list(length=1000)
    return {document["_id"] for document in documents}


async def mark_favorites(articles: list[Any]) -> list[Any]:
    ids = await favorite_ids()
    for article in articles:
        data = normalize_article(article)
        if isinstance(article, dict):
            article["id"] = data["id"]
            article["is_favorite"] = data["id"] in ids
        else:
            setattr(article, "id", data["id"])
            setattr(article, "is_favorite", data["id"] in ids)

    return articles


async def add_favorite(article: dict[str, Any]) -> None:
    favorite = normalize_article(article)
    favorite["_id"] = favorite["id"]
    favorite["saved_at"] = datetime.now(timezone.utc)
    await collection.replace_one({"_id": favorite["_id"]}, favorite, upsert=True)


async def remove_favorite(article_id: str) -> None:
    await collection.delete_one({"_id": article_id})
