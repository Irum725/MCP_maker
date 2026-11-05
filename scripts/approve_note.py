"""사람이 노트를 승인한다. 에이전트용 도구에는 일부러 승인 기능이 없다.

사용: uv run python scripts/approve_note.py list [project]   # 미승인 목록
      uv run python scripts/approve_note.py show <id>
      uv run python scripts/approve_note.py approve <id>
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from context_hub.db import Hub  # noqa: E402

hub = Hub(os.environ.get("HUB_DB", "hub_data/hub.db"))
cmd, *rest = sys.argv[1:] or ["list"]
if cmd == "list":
    with hub.conn() as c:
        q, args = "SELECT id,project,kind,title,author FROM notes WHERE status='draft'", []
        if rest:
            q += " AND project=?"; args.append(rest[0])
        for r in c.execute(q + " ORDER BY id", args):
            print(f"#{r['id']} [{r['project']}/{r['kind']}] {r['title']} (by {r['author']})")
elif cmd == "show":
    n = hub.read_note(int(rest[0]))
    print(f"#{n['id']} {n['title']} by {n['author']} [{n['status']}]\nref: {n['ref']}\n\n{n['body']}")
elif cmd == "approve":
    hub.approve_note(int(rest[0]), "human")
    print(f"노트 {rest[0]} 승인됨")
else:
    sys.exit(__doc__)
