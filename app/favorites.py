import json
from dataclasses import asdict, is_dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any


FAVORITES_PATH = Path(__file__).resolve().parent.parent / "favorites.json"


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
    normalized["id"] = article_key(normalized)
    normalized["is_favorite"] = True
    return normalized


def load_favorites() -> list[dict[str, Any]]:
    try:
        with open(FAVORITES_PATH, encoding="utf-8") as file:
            favorites = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    if not isinstance(favorites, list):
        return []

    return [normalize_article(article) for article in favorites if isinstance(article, dict)]


def save_favorites(favorites: list[dict[str, Any]]) -> None:
    with open(FAVORITES_PATH, "w", encoding="utf-8") as file:
        json.dump(favorites, file, ensure_ascii=False, indent=2)


def favorite_ids() -> set[str]:
    return {favorite["id"] for favorite in load_favorites()}


def mark_favorites(articles: list[Any]) -> list[Any]:
    ids = favorite_ids()
    for article in articles:
        data = normalize_article(article)
        if isinstance(article, dict):
            article["id"] = data["id"]
            article["is_favorite"] = data["id"] in ids
        else:
            setattr(article, "id", data["id"])
            setattr(article, "is_favorite", data["id"] in ids)

    return articles


def add_favorite(article: dict[str, Any]) -> None:
    favorite = normalize_article(article)
    favorites = load_favorites()
    remaining = [item for item in favorites if item["id"] != favorite["id"]]
    save_favorites([favorite, *remaining])


def remove_favorite(article_id: str) -> None:
    favorites = load_favorites()
    save_favorites([item for item in favorites if item["id"] != article_id])
