from pathlib import Path

import aiohttp
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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
    return await client.search(keyword, display=display, start=start, sort=sort)


def naver_error_message(error: aiohttp.ClientResponseError) -> str:
    if error.status == 401:
        return "네이버 API 인증에 실패했습니다. NAVER_API_ID와 NAVER_API_SECRET 값을 확인해주세요."

    return f"네이버 API 요청에 실패했습니다. 상태 코드: {error.status}"


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "title": "네이버 뉴스 검색",
            "articles": [],
            "sort_options": SORT_OPTIONS,
            "sort": "date",
            "display": 10,
        },
    )


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
            {
                "title": "네이버 뉴스 검색",
                "articles": [],
                "message": "검색어를 입력해주세요.",
                "sort_options": SORT_OPTIONS,
                "sort": sort,
                "display": display,
            },
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
        {
            "title": "네이버 뉴스 검색",
            "keyword": keyword,
            "articles": articles,
            "message": message,
            "sort_options": SORT_OPTIONS,
            "sort": sort,
            "display": display,
        },
    )


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
