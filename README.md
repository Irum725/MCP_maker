# Context Hub MCP

Antigravity, Claude Code, 로컬 AI(Ollama)가 **같은 MCP 서버 하나**에 연결해 작업 기억(노트·할 일·결정·인수인계)을 공유하는 프로젝트.
협업 규칙은 [AGENTS.md](AGENTS.md)가 단일 원본이다.

```
Antigravity ─┐
Claude Code ─┼─► http://127.0.0.1:8765/mcp  (Bearer 토큰, stateless)
Ollama(ollmcp)┘          └── hub_data/hub.db (SQLite WAL + FTS5)
```

## 1단계에 들어 있는 것
| 항목 | 위치 |
|---|---|
| SQLite 스키마(노트·FTS5·작업·세션·감사 로그) | `context_hub/schema.sql`, `context_hub/db.py` |
| 토큰 인증(Bearer + Origin 검사, 해시 저장) | `context_hub/auth.py`, `scripts/gen_tokens.py` |
| 서버(도구 10개 + 시작 프롬프트) | `context_hub/server.py` |
| 사람용 노트 승인 CLI | `scripts/approve_note.py` |
| 도구 선택 정확도 평가 틀 | `eval/run_eval.py`, `eval/scenarios.json` |

## 빠른 시작
```bash
uv sync
uv run python scripts/gen_tokens.py          # 에이전트별 토큰 발급 (평문은 이때 한 번만 표시)
uv run python -m context_hub.server          # 127.0.0.1:8765 에서 실행
```
환경변수: `HUB_PORT`(8765), `HUB_DB`(hub_data/hub.db), `HUB_TOKENS`(tokens.json)

### 검증
```bash
uv run pytest -q
uv run python eval/run_eval.py --dry-run
npx @modelcontextprotocol/inspector          # 브라우저에서 직접 호출 (URL과 Authorization 헤더 입력)
```

## 클라이언트 연결
발급된 토큰을 환경변수로 두고 설정에는 평문을 직접 쓰지 않는다. (아래 설정 형식은 클라이언트 버전에 따라 다를 수 있으니 각 문서로 확인)

- **Claude Code:** `claude mcp add --transport http --scope project context-hub http://127.0.0.1:8765/mcp --header "Authorization: Bearer $HUB_TOKEN_CLAUDE"`
- **Antigravity:** `~/.gemini/config/mcp_config.json`
  ```json
  { "mcpServers": { "context-hub": {
      "serverUrl": "http://127.0.0.1:8765/mcp",
      "headers": { "Authorization": "Bearer <antigravity 토큰>" } } } }
  ```
- **로컬 AI(ollmcp):** `.mcp.json` 호환 설정에 같은 URL과 `local` 토큰 헤더를 지정한다.

## 도구 선택 평가 (로컬 모델)
```bash
HUB_TOKEN=<local 토큰> uv run python eval/run_eval.py --model qwen3:8b --repeat 3
```
결과 CSV는 `eval/results/`(gitignore)에 쌓인다. 도구 설명을 고칠 때마다 돌려 정답률을 비교한다.

## 설계 메모
- **신원은 토큰이 정한다.** 도구에 `author` 인자가 없어서 모델이 속일 수 없다.
- **노트는 항상 draft로 시작**하고 사람이 승인해야 `trusted`가 된다 (프롬프트 주입 완화).
- **작업 점유는 리스 기반**이라 점유한 AI가 죽어도 만료 후 다른 AI가 이어받는다.
- **검색은 trigram FTS5**라 한국어 조사("SQLite와")가 붙어도 찾는다. 2글자 이하는 LIKE로 대체한다.
- 프로토콜 세션에 상태를 숨기지 않고 `task_id`/`session_id` 핸들을 쓴다 (MCP 2026-07-28 stateless 방향).

## 다음 단계 (2단계 이후)
승인 흐름 MRTR, Tasks 확장, 작업 완료 시 git 자동 커밋, 프로젝트별 네임스페이스 정책, 인증 고도화.
