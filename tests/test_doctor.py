import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import doctor  # noqa: E402


def test_tokens_missing_empty_and_ok(tmp_path):
    assert doctor.check_tokens(tmp_path / "none.json")[0] is False
    (tmp_path / "e.json").write_text(json.dumps({"agents": {}}))
    assert doctor.check_tokens(tmp_path / "e.json")[0] is False
    (tmp_path / "bad.json").write_text("{not json")
    assert doctor.check_tokens(tmp_path / "bad.json")[0] is False
    (tmp_path / "ok.json").write_text(json.dumps({"agents": {"claude": {"sha256": "x"}}}))
    ok, msg, _ = doctor.check_tokens(tmp_path / "ok.json")
    assert ok and "claude" in msg


def test_foreign_venv_is_detected(tmp_path):
    assert doctor.check_venv(tmp_path)[0] is False  # .venv 없음
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "pyvenv.cfg").write_text("home = /nonexistent/other/os/bin\n")
    ok, msg, hint = doctor.check_venv(tmp_path)
    assert not ok and "rm -rf .venv" in hint
    (tmp_path / ".venv" / "pyvenv.cfg").write_text(f"home = {tmp_path}\n")
    assert doctor.check_venv(tmp_path)[0] is True


def test_server_down_gives_next_step():
    ok, _, hint = doctor.check_server("http://127.0.0.1:9/mcp", timeout=0.5)
    assert not ok and "context_hub.server" in hint
