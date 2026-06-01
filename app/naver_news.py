import asyncio
import re
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from html import unescape
from urllib.parse import urljoin, urlencode

import aiohttp

from app.config import get_secret


def clean_html(value: str) -> str:
    text = unescape(value or "")
    return re.sub(r"<[^>]+>", "", text)


def format_pub_date(value: str) -> str:
    if not value:
        return ""

    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return value

    return parsed.strftime("%Y-%m-%d %H:%M")


@dataclass
class NewsArticle:
    title: str
    originallink: str
    link: str
    description: str
    pub_date: str
    image_url: str = ""

    @classmethod
    def from_api_item(cls, item: dict):
        return cls(
            title=clean_html(item.get("title", "")),
            originallink=item.get("originallink", ""),
            link=item.get("link", ""),
            description=clean_html(item.get("description", "")),
            pub_date=format_pub_date(item.get("pubDate", "")),
        )


def find_meta_image(html: str, base_url: str) -> str:
    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
        r'<img[^>]+src=["\']([^"\']+)["\']',
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.IGNORECASE)
        if match:
            return urljoin(base_url, unescape(match.group(1)))

    return ""


class NaverNewsClient:
    NAVER_API_NEWS = "https://openapi.naver.com/v1/search/news.json"

    def __init__(self):
        self.client_id = get_secret("NAVER_API_ID")
        self.client_secret = get_secret("NAVER_API_SECRET")

    @property
    def headers(self):
        return {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        }

    @property
    def article_headers(self):
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    def build_url(self, keyword: str, display: int, start: int, sort: str) -> str:
        query_string = urlencode(
            {
                "query": keyword,
                "display": display,
                "start": start,
                "sort": sort,
            }
        )
        return f"{self.NAVER_API_NEWS}?{query_string}"

    async def fetch_page(self, session, keyword: str, display: int, start: int, sort: str):
        url = self.build_url(keyword, display, start, sort)

        async with session.get(url, headers=self.headers) as response:
            response.raise_for_status()
            result = await response.json()
            return result.get("items", [])

    async def fetch_article_image(self, session, article: NewsArticle, semaphore):
        url = article.originallink or article.link
        if not url:
            return article

        try:
            async with semaphore:
                async with session.get(url, headers=self.article_headers, allow_redirects=True) as response:
                    if response.status >= 400:
                        return article

                    html = await response.text(errors="ignore")
                    article.image_url = find_meta_image(html, str(response.url))
        except (aiohttp.ClientError, asyncio.TimeoutError, UnicodeDecodeError):
            return article

        return article

    async def search(self, keyword: str, display: int = 10, start: int = 1, sort: str = "date"):
        display = max(1, min(display, 100))
        start = max(1, min(start, 1000))
        sort = sort if sort in {"sim", "date"} else "date"

        timeout = aiohttp.ClientTimeout(total=6)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            items = await self.fetch_page(session, keyword, display, start, sort)
            articles = [NewsArticle.from_api_item(item) for item in items]
            semaphore = asyncio.Semaphore(5)
            await asyncio.gather(
                *[self.fetch_article_image(session, article, semaphore) for article in articles]
            )

        return articles

    def run(self, keyword: str, display: int = 10, start: int = 1, sort: str = "date"):
        return asyncio.run(self.search(keyword, display, start, sort))
