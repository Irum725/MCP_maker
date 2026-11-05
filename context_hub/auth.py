"""토큰 인증. 평문 토큰은 저장하지 않고 SHA-256 해시만 tokens.json에 둔다.

- 신원(author)은 항상 토큰으로 서버가 결정한다. 모델이 스스로 적게 하지 않는다.
- 로컬 서버라도 아무 프로세스나 접속하지 못하게 Bearer 토큰을 요구하고,
  브라우저 페이지의 로컬 호출(DNS rebinding 등)을 막기 위해 Origin을 검사한다.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_AGENTS = ("antigravity", "claude", "local")


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_token() -> str:
    return "hub_" + secrets.token_urlsafe(32)


def load_tokens(path: str | Path) -> dict[str, str]:
    """{에이전트 이름: sha256} 반환. 파일이 없거나 비어 있으면 오류."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"{p} 없음. `uv run python scripts/gen_tokens.py`로 먼저 발급하세요")
    data = json.loads(p.read_text(encoding="utf-8"))
    agents = {name: v["sha256"] for name, v in data.get("agents", {}).items()}
    if not agents:
        raise ValueError(f"{p}에 등록된 에이전트가 없습니다")
    return agents


def identify(token: str | None, agents: dict[str, str]) -> str | None:
    """상수 시간 비교로 토큰 소유자 이름을 찾는다."""
    if not token:
        return None
    digest = hash_token(token)
    found = None
    for name, h in agents.items():  # 일치해도 끝까지 순회 (타이밍 누출 방지)
        if hmac.compare_digest(digest, h):
            found = name
    return found


def bearer(header_value: str | None) -> str | None:
    if not header_value:
        return None
    scheme, _, tok = header_value.partition(" ")
    return tok.strip() if scheme.lower() == "bearer" and tok.strip() else None


def origin_allowed(origin: str | None, allowed_hosts: set[str]) -> bool:
    """Origin 헤더가 없으면(CLI/SDK 클라이언트) 통과, 있으면 허용 호스트여야 한다."""
    if origin is None:
        return True
    host = urlparse(origin).hostname
    return host in allowed_hosts


class AuthMiddleware:
    """순수 ASGI 미들웨어: 인증 실패는 MCP 처리 전에 401/403으로 끊는다."""

    def __init__(self, app, agents: dict[str, str], allowed_hosts: set[str] | None = None):
        self.app = app
        self.agents = agents
        self.allowed_hosts = allowed_hosts or {"127.0.0.1", "localhost"}

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {k.decode("latin1").lower(): v.decode("latin1") for k, v in scope["headers"]}
        if not origin_allowed(headers.get("origin"), self.allowed_hosts):
            return await self._deny(send, 403, "허용되지 않은 Origin")
        if identify(bearer(headers.get("authorization")), self.agents) is None:
            return await self._deny(send, 401, "유효한 Bearer 토큰이 필요합니다")
        return await self.app(scope, receive, send)

    @staticmethod
    async def _deny(send, status: int, msg: str):
        body = json.dumps({"error": msg}, ensure_ascii=False).encode("utf-8")
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"content-type", b"application/json; charset=utf-8"),
                                (b"www-authenticate", b"Bearer")]})
        await send({"type": "http.response.body", "body": body})
