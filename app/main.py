from pathlib import Path

import aiohttp
from fastapi import FastAPI, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.favorites import add_favorite, load_favorites, mark_favorites, remove_favorite
from app.naver_news import NaverNewsClient


app = FastAPI(title="Naver News Search")


BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


SORT_OPTIONS = {
    "date": "최신순",
    "sim": "정확도순",
}


async def search_news(keyword: str, display: int, start: int, sort: str):
    client = NaverNewsClient()
    articles = await client.search(keyword, display=display, start=start, sort=sort)
    return mark_favorites(articles)


def naver_error_message(error: aiohttp.ClientResponseError) -> str:
    if error.status == 401:
        return "네이버 API 인증에 실패했습니다. NAVER_API_ID와 NAVER_API_SECRET 값을 확인해주세요."

    return f"네이버 API 요청에 실패했습니다. 상태 코드: {error.status}"


def page_context(**values):
    context = {
        "title": "네이버 뉴스 검색",
        "keyword": "",
        "articles": [],
        "message": None,
        "sort_options": SORT_OPTIONS,
        "sort": "date",
        "display": 10,
        "page": "search",
    }
    context.update(values)
    return context


def back_to_sender(request: Request, fallback: str = "/favorites"):
    target = request.headers.get("referer") or fallback
    return RedirectResponse(target, status_code=303)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(request, "index.html", page_context())


@app.get("/search", response_class=HTMLResponse)
async def search_page(
    request: Request,
    q: str = "",
    display: int = Query(default=10, ge=1, le=100),
    start: int = Query(default=1, ge=1, le=1000),
    sort: str = "date",
):
    keyword = q.strip()
    sort = sort if sort in SORT_OPTIONS else "date"

    if not keyword:
        return templates.TemplateResponse(
            request,
            "index.html",
            page_context(
                message="검색어를 입력해주세요.",
                sort=sort,
                display=display,
            ),
        )

    message = None
    articles = []

    try:
        articles = await search_news(keyword, display, start, sort)
        if not articles:
            message = "검색 결과가 없습니다."
    except aiohttp.ClientResponseError as error:
        message = naver_error_message(error)
    except Exception:
        message = "뉴스 검색 중 오류가 발생했습니다. API 키와 네트워크 상태를 확인해주세요."

    return templates.TemplateResponse(
        request,
        "index.html",
        page_context(
            keyword=keyword,
            articles=articles,
            message=message,
            sort=sort,
            display=display,
        ),
    )


@app.get("/favorites", response_class=HTMLResponse)
async def favorites_page(request: Request):
    favorites = load_favorites()
    message = None if favorites else "아직 즐겨찾기한 기사가 없습니다."

    return templates.TemplateResponse(
        request,
        "index.html",
        page_context(
            title="즐겨찾기",
            articles=favorites,
            message=message,
            page="favorites",
        ),
    )


@app.post("/favorites")
async def create_favorite(
    request: Request,
    title: str = Form(default=""),
    originallink: str = Form(default=""),
    link: str = Form(default=""),
    description: str = Form(default=""),
    pub_date: str = Form(default=""),
    image_url: str = Form(default=""),
):
    add_favorite(
        {
            "title": title,
            "originallink": originallink,
            "link": link,
            "description": description,
            "pub_date": pub_date,
            "image_url": image_url,
        }
    )
    return back_to_sender(request, "/favorites")


@app.post("/favorites/delete")
async def delete_favorite(request: Request, article_id: str = Form(...)):
    remove_favorite(article_id)
    return back_to_sender(request, "/favorites")


@app.get("/api/news")
async def search_news_api(
    q: str,
    display: int = Query(default=10, ge=1, le=100),
    start: int = Query(default=1, ge=1, le=1000),
    sort: str = "date",
):
    keyword = q.strip()
    sort = sort if sort in SORT_OPTIONS else "date"

    try:
        articles = await search_news(keyword, display, start, sort)
    except aiohttp.ClientResponseError as error:
        raise HTTPException(status_code=error.status, detail=naver_error_message(error)) from error

    return {"keyword": keyword, "total": len(articles), "items": articles}


@app.get("/api/favorites")
async def favorites_api():
    favorites = load_favorites()
    return {"total": len(favorites), "items": favorites}
