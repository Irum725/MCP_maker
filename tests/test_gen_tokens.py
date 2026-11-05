import json
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_env_out_saves_plain_tokens_privately_and_hashes_only_in_json(tmp_path):
    out, env = tmp_path / "tokens.json", tmp_path / ".hub_env"
    r = subprocess.run([sys.executable, str(ROOT / "scripts/gen_tokens.py"), "--out", str(out),
                        "--env-out", str(env), "claude", "local"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    plain = dict(line.removeprefix("export ").split("=", 1) for line in env.read_text().splitlines())
    assert set(plain) == {"HUB_TOKEN_CLAUDE", "HUB_TOKEN_LOCAL"}
    token = plain["HUB_TOKEN_CLAUDE"].strip("'")
    assert token.startswith("hub_")
    assert token not in out.read_text()                      # tokens.json에는 해시만 있다
    assert stat.S_IMODE(env.stat().st_mode) == 0o600          # 본인만 읽기 가능
    assert json.loads(out.read_text())["agents"]["claude"]["sha256"]


def test_refuses_overwrite_without_force(tmp_path):
    out = tmp_path / "tokens.json"
    out.write_text("{}")
    r = subprocess.run([sys.executable, str(ROOT / "scripts/gen_tokens.py"), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode != 0 and "--force" in r.stderr
