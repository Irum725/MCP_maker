"""실제 서버 프로세스를 띄워 HTTP 경로(인증·Origin·신원 결정)를 검증한다."""
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from context_hub.auth import hash_token, new_token

ROOT = Path(__file__).resolve().parent.parent


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    d = tmp_path_factory.mktemp("hub")
    toks = {n: new_token() for n in ("claude", "local")}
    (d / "tokens.json").write_text(json.dumps(
        {"agents": {n: {"sha256": hash_token(t)} for n, t in toks.items()}}))
    port = _free_port()
    env = os.environ | {"HUB_DB": str(d / "hub.db"), "HUB_TOKENS": str(d / "tokens.json"),
                        "HUB_PORT": str(port), "PYTHONPATH": str(ROOT)}
    p = subprocess.Popen([sys.executable, "-m", "context_hub.server"], env=env, cwd=ROOT,
                         stderr=subprocess.PIPE)
    url = f"http://127.0.0.1:{port}/mcp"
    for _ in range(100):
        try:
            httpx.get(url, timeout=0.5)
            break
        except httpx.HTTPError:
            time.sleep(0.1)
    else:
        p.kill()
        pytest.fail("서버가 뜨지 않음: " + p.stderr.read().decode())
    yield url, toks, d
    p.terminate()
    p.wait(timeout=5)


def test_rejects_without_or_wrong_token(server):
    url, _, _ = server
    assert httpx.post(url, json={}).status_code == 401
    assert httpx.post(url, json={}, headers={"Authorization": "Bearer nope"}).status_code == 401


def test_rejects_foreign_origin(server):
    url, toks, _ = server
    r = httpx.post(url, json={}, headers={"Authorization": f"Bearer {toks['claude']}",
                                          "Origin": "http://evil.example"})
    assert r.status_code == 403


async def test_author_is_decided_by_token_and_tools_work(server):
    url, toks, _ = server
    async with Client(url, auth=toks["claude"]) as c:
        names = {t.name for t in await c.list_tools()}
        assert {"start_session", "add_note", "claim_task"} <= names
        r = await c.call_tool("add_note", {"project": "demo", "title": "결정", "body": "토큰으로 신원 결정"})
        nid = r.data["id"]
    async with Client(url, auth=toks["local"]) as c:
        note = (await c.call_tool("read_note", {"note_id": nid})).data
        assert note["author"] == "claude" and note["status"] == "draft" and "warning" in note
        # 모델이 author를 속일 수 있는 인자는 아예 존재하지 않는다
        tool = next(t for t in await c.list_tools() if t.name == "add_note")
        assert "author" not in tool.input_schema["properties"] and "me" not in tool.input_schema["properties"]


async def test_claim_conflict_between_agents(server):
    url, toks, _ = server
    async with Client(url, auth=toks["claude"]) as c1, Client(url, auth=toks["local"]) as c2:
        tid = (await c1.call_tool("create_task", {"project": "demo", "title": "t"})).data["task_id"]
        await c1.call_tool("claim_task", {"task_id": tid})
        with pytest.raises(ToolError):
            await c2.call_tool("claim_task", {"task_id": tid})
        with pytest.raises(ToolError):
            await c2.call_tool("complete_task", {"task_id": tid, "result": "탈취"})


async def test_audit_log_records_calls(server):
    url, toks, d = server
    async with Client(url, auth=toks["claude"]) as c:
        await c.call_tool("list_tasks", {"project": "demo"})
    import sqlite3
    rows = sqlite3.connect(d / "hub.db").execute(
        "SELECT agent, tool, ok FROM audit_log WHERE tool='list_tasks'").fetchall()
    assert ("claude", "list_tasks", 1) in rows
