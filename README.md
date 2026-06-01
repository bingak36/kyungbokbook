# 네이버 뉴스 검색 API 앱

FastAPI로 만든 네이버 뉴스 검색 API 응용 프로그램입니다.

## 실행 방법

1. `secrets.json` 또는 환경 변수에 네이버 API 키를 설정합니다. 뉴스 검색 기능은 MongoDB 없이 실행됩니다.

```json
{
  "NAVER_API_ID": "네이버_CLIENT_ID",
  "NAVER_API_SECRET": "네이버_CLIENT_SECRET"
}
```

2. 서버를 실행합니다.

```bash
uvicorn app.main:app --reload
```

3. 브라우저에서 `http://127.0.0.1:8000`에 접속합니다.

## API

```text
GET /api/news?q=검색어&display=10&start=1&sort=date
```

- `q`: 검색어
- `display`: 표시 개수, 1~100
- `start`: 검색 시작 위치, 1~1000
- `sort`: `date` 최신순, `sim` 정확도순

## Vercel 배포

Vercel은 `app/index.py`에서 FastAPI 앱을 찾습니다.

Vercel 프로젝트 설정의 Environment Variables에 아래 값을 추가해야 합니다.

- `NAVER_API_ID`
- `NAVER_API_SECRET`

`secrets.json`은 Git에 올리지 않는 로컬 개발용 파일입니다.
