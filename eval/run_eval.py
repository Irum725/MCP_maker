"""도구 선택 정확도 평가. '로컬 모델이 헷갈리지 않는 설명이면 큰 모델에서도 잘 동작한다'는 가설 검증용.

사용:
  uv run python eval/run_eval.py --dry-run                      # 시나리오가 실제 도구와 맞는지 결정론적으로 검증(모델 불필요)
  uv run python eval/run_eval.py --model qwen3:8b               # Ollama로 측정 (HUB_TOKEN 필요, 서버 실행 중이어야 함)
  uv run python eval/run_eval.py --model qwen3:8b --repeat 3    # 반복 측정

결과는 eval/results/<모델>-<시각>.csv 에 저장된다(gitignore). 도구 설명을 바꿀 때마다 돌려 정답률을 비교한다.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SCENARIOS = ROOT / "eval" / "scenarios.json"


def load_scenarios(path: Path = SCENARIOS) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


async def fetch_tools(url: str | None):
    """(이름, 설명, 파라미터 스키마) 목록. url이 없으면 인메모리 서버에서 읽는다."""
    if url is None:
        from context_hub.db import Hub
        from context_hub.server import build_server
        mcp = build_server(Hub(":memory:"), {"dry": "0" * 64})
        return [(t.name, t.description or "", t.parameters) for t in await mcp.list_tools()]
    from fastmcp import Client
    async with Client(url, auth=os.environ["HUB_TOKEN"]) as c:
        return [(t.name, t.description or "", t.input_schema) for t in await c.list_tools()]


def validate(scenarios: list[dict], tools) -> list[str]:
    """결정론적 검증: 기대 도구가 존재하는지, 기대 인자가 스키마에 있는지, id 중복이 없는지."""
    names = {n: schema for n, _, schema in tools}
    errs, seen = [], set()
    for s in scenarios:
        if s["id"] in seen:
            errs.append(f"{s['id']}: id 중복")
        seen.add(s["id"])
        if s["expect_tool"] not in names:
            errs.append(f"{s['id']}: 없는 도구 {s['expect_tool']}")
            continue
        props = (names[s["expect_tool"]] or {}).get("properties", {})
        for a in s.get("expect_args", {}):
            if a not in props:
                errs.append(f"{s['id']}: {s['expect_tool']}에 인자 {a} 없음")
    return errs


def score(call: dict | None, s: dict) -> tuple[bool, bool]:
    """(도구 정답, 인자 정답). 인자는 expect_args의 부분 일치만 본다."""
    if not call or call["name"] != s["expect_tool"]:
        return False, False
    got = call.get("arguments", {})
    args_ok = all(str(got.get(k)) == str(v) for k, v in s.get("expect_args", {}).items())
    return True, args_ok


def ask_ollama(host: str, model: str, prompt: str, tools) -> dict | None:
    """Ollama /api/chat 도구 호출. 첫 tool_call을 반환(없으면 None)."""
    import httpx
    payload = {"model": model, "stream": False,
               "messages": [{"role": "user", "content": prompt}],
               "tools": [{"type": "function", "function": {"name": n, "description": d, "parameters": p}}
                         for n, d, p in tools]}
    r = httpx.post(f"{host}/api/chat", json=payload, timeout=120)
    r.raise_for_status()
    calls = r.json().get("message", {}).get("tool_calls") or []
    return {"name": calls[0]["function"]["name"], "arguments": calls[0]["function"].get("arguments", {})} if calls else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model")
    ap.add_argument("--url", default="http://127.0.0.1:8765/mcp")
    ap.add_argument("--ollama", default="http://127.0.0.1:11434")
    ap.add_argument("--repeat", type=int, default=1)
    a = ap.parse_args()

    scenarios = load_scenarios()
    tools = asyncio.run(fetch_tools(None if a.dry_run else a.url))
    errs = validate(scenarios, tools)
    if errs:
        print("\n".join(errs), file=sys.stderr)
        return 1
    if a.dry_run:
        print(f"OK: 시나리오 {len(scenarios)}개가 도구 {len(tools)}개와 일치합니다")
        return 0
    if not a.model:
        sys.exit("--model 이 필요합니다 (또는 --dry-run)")

    rows, ok_tool, ok_args = [], 0, 0
    for s in scenarios:
        for i in range(a.repeat):
            t0 = time.perf_counter()
            try:
                call = ask_ollama(a.ollama, a.model, s["prompt"], tools)
            except Exception as e:  # 모델 오류도 기록하고 계속
                call, err = None, str(e)
            else:
                err = ""
            t_ok, a_ok = score(call, s)
            ok_tool += t_ok
            ok_args += a_ok
            rows.append({"id": s["id"], "run": i, "expect": s["expect_tool"],
                         "got": call["name"] if call else "", "tool_ok": int(t_ok), "args_ok": int(a_ok),
                         "ms": int((time.perf_counter() - t0) * 1000), "error": err})
    n = len(rows)
    out = ROOT / "eval" / "results"
    out.mkdir(exist_ok=True)
    f = out / f"{a.model.replace(':', '_')}-{time.strftime('%Y%m%d-%H%M%S')}.csv"
    with f.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"{a.model}: 도구 선택 {ok_tool}/{n} ({ok_tool/n:.0%}), 인자까지 {ok_args}/{n} ({ok_args/n:.0%}) → {f}")
    for r in rows:
        if not r["tool_ok"]:
            print(f"  ✗ {r['id']}: 기대 {r['expect']} / 실제 {r['got'] or '(호출 없음)'} {r['error']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
