"""Optional loopback HTTP redirect for the homelab HTTPS listener."""
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from ai_interviewer.config import Settings


def build_redirect():
    target = Settings().public_base_url.rstrip("/")
    if not target.startswith("https://"):
        raise ValueError("HTTP redirect requires an HTTPS PUBLIC_BASE_URL")
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @app.api_route("/{path:path}", methods=["GET", "HEAD"])
    async def redirect(request: Request, path: str):
        response = RedirectResponse(target + request.url.path, status_code=307)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    return app


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(build_redirect(), host="127.0.0.1", port=8000, workers=1, access_log=False)
