import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "eval"))
import run_eval as ev  # noqa: E402


def test_scenarios_match_real_tools():
    """시나리오가 실제 서버 도구와 어긋나면(도구 이름/인자 변경) 바로 실패한다."""
    tools = asyncio.run(ev.fetch_tools(None))
    assert ev.validate(ev.load_scenarios(), tools) == []


def test_validate_catches_bad_scenarios():
    tools = [("a", "", {"properties": {"x": {}}})]
    bad = [{"id": "1", "prompt": "", "expect_tool": "nope"},
           {"id": "2", "prompt": "", "expect_tool": "a", "expect_args": {"y": 1}},
           {"id": "2", "prompt": "", "expect_tool": "a"}]
    assert len(ev.validate(bad, tools)) == 3


def test_score():
    s = {"expect_tool": "claim_task", "expect_args": {"task_id": 3}}
    assert ev.score({"name": "claim_task", "arguments": {"task_id": "3"}}, s) == (True, True)
    assert ev.score({"name": "claim_task", "arguments": {"task_id": 4}}, s) == (True, False)
    assert ev.score({"name": "read_note", "arguments": {}}, s) == (False, False)
    assert ev.score(None, s) == (False, False)
