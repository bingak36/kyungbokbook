import re
from html import unescape
from pathlib import Path
from urllib.parse import parse_qs

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.book_scraper import NaverBookScraper
from app.models import mongodb
from app.models.book import BookModel


app = FastAPI()


BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


DB_ERROR_MESSAGE = "즐겨찾기 DB 연결을 확인해주세요."


def clean_html(value: str) -> str:
    return unescape(re.sub(r"<[^>]+>", "", value or ""))


def parse_price(value: str | int | None) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {"title": "북북", "books": [], "next_url": "/"},
    )


@app.get("/search", response_class=HTMLResponse)
async def read_item(request: Request, q: str = ""):
    keyword = q.strip()

    if not keyword:
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "title": "북북",
                "books": [],
                "message": "검색어를 입력해주세요.",
                "next_url": "/",
            },
        )

    naver_book_scraper = NaverBookScraper()
    books = await naver_book_scraper.search(keyword, 10)

    message = None
    try:
        favorite_books = await mongodb.engine.find(BookModel, BookModel.is_favorite == True)
        favorite_images = [book.image for book in favorite_books]
    except Exception:
        favorite_images = []
        message = DB_ERROR_MESSAGE

    book_models = [
        BookModel(
            keyword=keyword,
            publisher=clean_html(book.get("publisher", "")),
            price=parse_price(book.get("discount")),
            image=book.get("image", ""),
        )
        for book in books
    ]

    for book_model in book_models:
        if book_model.image in favorite_images:
            book_model.is_favorite = True

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "title": "북북",
            "keyword": keyword,
            "books": book_models,
            "next_url": f"/search?q={keyword}",
            "message": message,
        },
    )


@app.post("/favorites")
async def toggle_favorite(request: Request):
    body = (await request.body()).decode()
    form = {key: values[0] for key, values in parse_qs(body).items()}

    keyword = form.get("keyword", "")
    publisher = form.get("publisher", "")
    price = parse_price(form.get("price"))
    image = form.get("image", "")
    next_url = form.get("next_url", "/")

    try:
        favorite_book = await mongodb.engine.find_one(
            BookModel,
            (BookModel.keyword == keyword)
            & (BookModel.publisher == publisher)
            & (BookModel.image == image)
            & (BookModel.is_favorite == True),
        )

        if favorite_book:
            await mongodb.engine.delete(favorite_book)
        else:
            book = BookModel(
                keyword=keyword,
                publisher=publisher,
                price=price,
                image=image,
                is_favorite=True,
            )
            await mongodb.engine.save(book)
    except Exception:
        return RedirectResponse(url=next_url, status_code=303)

    return RedirectResponse(url=next_url, status_code=303)


@app.get("/favorites", response_class=HTMLResponse)
async def favorites(request: Request):
    message = None
    try:
        books = await mongodb.engine.find(BookModel, BookModel.is_favorite == True)
    except Exception:
        books = []
        message = DB_ERROR_MESSAGE

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "title": "즐겨찾기 목록",
            "books": books,
            "next_url": "/favorites",
            "message": message,
        },
    )


@app.on_event("startup")
async def on_app_start():
    mongodb.connect()


@app.on_event("shutdown")
async def on_app_shutdown():
    mongodb.close()
