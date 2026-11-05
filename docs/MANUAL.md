# Context Hub 사용 매뉴얼 (AI별)

Claude Code, Antigravity, 로컬 AI(ollmcp)가 **같은 허브 서버**에 연결해 작업 기억을 공유하는 방법을 AI별로 설명한다.
협업 규칙은 [AGENTS.md](../AGENTS.md), 설치·구조는 [README.md](../README.md)를 본다.

> 이 문서의 연결 방식은 각 제품의 공식 문서(2026-11-05 확인)를 근거로 했다.
> 실제 연결 테스트는 사용자 환경에서 처음 해보는 것이므로, 막히면 각 절의 "문제 해결"과 마지막의 "확인 상태"를 본다.

---

## 0. 한눈에 보기

| | Claude Code | Antigravity | 로컬 AI (ollmcp) |
|---|---|---|---|
| 허브에서 맡는 역할 | 설계 검토, 코드 리뷰 | 메인 구현 | 반복 테스트, 도구 설명 검증 |
| 허브 에이전트 이름(토큰) | `claude` | `antigravity` | `local` |
| 연결 방법 | `connect-claude.command/.bat` | 설정 JSON 붙여넣기 | `ollmcp mcp add ...` |
| 승인 방식 | 처음 호출 시 권한 확인 | 기본 Ask(실행 전 승인) | `/hil` (기본 켜짐) |
| 설정 조각 출력 | `print_client_config.py claude` | `... antigravity` | `... ollmcp` |

**동작 흐름**

```
시작 → start_session → search_notes → claim_task → (작업) → complete_task → add_note(decision) → end_session(handoff)
사람: draft 노트를 읽어 보고 믿을 만하면 approve
```

## 1. 공통 준비 (한 번만)

1. 서버 실행: `start.command`(Mac) 또는 `start.bat`(Windows)를 더블클릭. **창은 켜 둔다.**
2. 최초 실행이면 토큰이 `.hub_env`에 저장된다(본인만 읽기 가능, git 제외).
3. 상태 점검: 터미널에서 `uv run python scripts/doctor.py` → 모두 ✓ 이면 준비 완료.
4. 각 AI의 설정 조각 보기: `uv run python scripts/print_client_config.py <claude|antigravity|ollmcp>`
   (**실제 토큰이 출력되니 화면 공유·캡처·채팅 붙여넣기 금지**)

토큰을 잃어버렸다면: `uv run python scripts/gen_tokens.py --force --env-out .hub_env` → 기존 토큰이 전부 무효화되므로 서버를 재시작하고 각 AI의 연결을 다시 등록한다.

---

## 2. Claude Code

### 연결
가장 쉬운 방법은 `connect-claude.command`(Windows는 `.bat`)를 더블클릭하는 것이다. 수동으로 하려면:

```bash
claude mcp add --transport http --scope local context-hub http://127.0.0.1:8765/mcp --header "Authorization: Bearer <claude 토큰>"
claude mcp list
```

- `--scope local`(기본값): 나만, 이 프로젝트에서만. 토큰이 `~/.claude.json`에 저장되어 저장소에 남지 않는다.
- ⚠ **`--scope project`는 쓰지 않는다.** 토큰이 저장소의 `.mcp.json`에 평문으로 들어가 공개 저장소로 유출될 수 있다.
- 여러 프로젝트에서 쓰려면 `--scope user`로 등록한다.
- 같은 이름이 여러 범위에 있으면 `claude mcp remove context-hub --scope local`처럼 범위를 지정한다.

### 상태 확인 (`claude mcp list`)
| 표시 | 뜻 | 조치 |
|---|---|---|
| `✔ Connected` | 정상 | 사용 시작 |
| `! Needs authentication` | 토큰이 없거나 틀림 | `--header`의 토큰 확인, 재등록 |
| `✘ Failed to connect` | 서버가 안 켜져 있거나 URL/토큰 오류 | `start.command` 실행 여부 확인, `claude mcp get context-hub`로 상세 오류 확인 |
| `⏸ Pending approval` | project 범위 서버 승인 대기 | (local 범위를 쓰면 나오지 않음) |

세션 안에서는 `/mcp`로 서버 상태를 보고 재연결할 수 있다. 처음 도구를 호출할 때 권한을 묻는 창이 뜨면 승인한다.

### 사용법
`claude`를 실행하고 평소처럼 말하면 필요할 때 도구를 호출한다. 확실히 쓰게 하려면 서버 이름을 말한다.

| 상황 | 이렇게 말한다 |
|---|---|
| 작업 시작 | "context-hub에서 프로젝트 `<이름>` 작업을 시작해. start_routine 순서대로 진행해줘." |
| 맥락 확인 | "context-hub에서 '인증' 관련 기존 결정이 있는지 찾아줘." |
| 일 나누기 | "오늘 할 일 3개를 context-hub 작업으로 등록해줘." |
| 일 맡기 | "열린 작업 중 첫 번째를 맡아서 진행하고, 끝나면 결과를 남겨줘." |
| 결정 남기기 | "방금 정한 방향을 decision 노트로 남겨줘. 관련 커밋은 ref에 적어줘." |
| 마무리 | "세션을 종료하고 다음 AI가 이어서 할 일을 인수인계에 써줘." |

**역할(리뷰):** 코드 리뷰나 설계 검토 결과는 `add_note(kind="note")`로 남기고, 구현 AI가 읽을 수 있게 `ref`에 파일·커밋을 적게 한다.

**자동으로 시작하게 하려면** 프로젝트 `CLAUDE.md`에 `AGENTS.md`가 이미 연결돼 있다(3번 루틴). 그래도 안 부르면 첫 문장에 "허브부터 확인해"를 붙인다.

### 문제 해결
- 도구가 안 보인다 → 연결한 폴더와 다른 폴더에서 `claude`를 실행했을 가능성(local 범위는 프로젝트별). 해당 폴더에서 다시 등록하거나 `--scope user`.
- 등록 직후엔 안 보이고 새 세션에서 보인다 → 세션을 다시 시작한다.
- 변경이 반영되지 않는다 → `claude mcp list`로 파싱 경고를 확인한다.

---

## 3. Antigravity

### 연결
설정 파일에 서버를 추가한다. 조각은 `print_client_config.py antigravity`가 토큰을 채워서 출력한다.

```json
{
  "mcpServers": {
    "context-hub": {
      "serverUrl": "http://127.0.0.1:8765/mcp",
      "headers": { "Authorization": "Bearer <antigravity 토큰>" },
      "timeoutSeconds": 600
    }
  }
}
```

| 위치 | 파일 / 메뉴 |
|---|---|
| **전역(권장)** | `~/.gemini/config/mcp_config.json` |
| 워크스페이스 | `<워크스페이스>/.agents/mcp_config.json` — ⚠ 저장소 안이라 **토큰이 커밋될 수 있어 비권장** |
| App UI | 사이드바 **Customizations → Installed → MCP Servers → +** |
| IDE | 에이전트 패널 **… → MCP Servers → Manage MCP Servers → View raw config** |
| CLI | 프롬프트에 `/mcp` (연결 상태 확인, 설정 다시 불러오기) |

- 원격 서버는 **Streamable HTTP**만 지원한다(이 허브가 쓰는 방식과 같다). `httpUrl` 필드나 SSE는 쓰지 않는다.
- 기존 파일에 다른 서버가 있다면 `mcpServers` 안에 `context-hub` 항목만 **추가**한다(덮어쓰지 않는다).
- 저장 후 서버 목록에서 재시작하거나 `/mcp`로 다시 불러온다.

### 승인과 권한
- MCP 도구는 기본 **Ask**: 실행 전에 매번 승인을 묻는다. 처음에는 이대로 두고 동작을 확인한다.
- 신뢰가 쌓이면 권한 정책으로 허용할 수 있다. 패턴: `mcp(context-hub/search_notes)` 한 개, `mcp(context-hub/*)` 서버 전체, `mcp(*)` 전부(비권장).
- 읽기 도구만 먼저 허용하는 것을 권한다: `search_notes`, `read_note`, `list_tasks`, `start_session`.

### 도구 제한 (역할별 프로필)
`enabledTools`(허용 목록) 또는 `disabledTools`(거부 목록)로 노출 도구를 줄인다. 도구가 적을수록 헷갈릴 일이 줄어든다.

```json
"context-hub": {
  "serverUrl": "http://127.0.0.1:8765/mcp",
  "headers": { "Authorization": "Bearer <토큰>" },
  "enabledTools": ["start_session", "search_notes", "read_note", "list_tasks"]
}
```
위 예시는 **읽기 전용 프로필**이다. 구현 담당 Antigravity에는 보통 전체 도구를 열어 둔다.

### 사용법
| 상황 | 이렇게 말한다 |
|---|---|
| 작업 이어받기 | "context-hub에서 프로젝트 `<이름>`의 최근 인수인계와 열린 작업을 확인하고 이어서 진행해." |
| 작업 점유 | "열린 작업 중 하나를 claim_task로 맡고, 30분 넘으면 heartbeat_task로 연장해." |
| 완료 | "작업 끝났어. complete_task로 결과를 남기고, 중요한 결정은 decision 노트로 기록해." |
| 종료 | "end_session으로 요약과 다음 할 일을 인수인계에 남겨줘." |

타임아웃: 기본은 도구 호출당 180초, 서버 연결·목록 조회 300초다. 이 허브의 도구는 즉시 끝나므로 기본값으로 충분하다(위 예시의 600은 여유값).

### 문제 해결
- 서버가 안 뜬다/도구가 안 보인다 → `start.command`가 켜져 있는지, `uv run python scripts/doctor.py`가 ✓인지 확인. JSON 문법(쉼표, 따옴표)을 확인한다.
- 401/인증 오류 → `headers`의 토큰이 `antigravity` 토큰인지, 재발급 후 갱신했는지 확인.
- 매번 승인 창이 귀찮다 → 위 권한 정책으로 읽기 도구부터 허용한다.

---

## 4. 로컬 AI (ollmcp = MCP client for Ollama)

### 사전 조건
- Ollama가 실행 중이고, **도구 호출(tools)을 지원하는 모델**이 받아져 있어야 한다. 공식 README가 잘 동작한다고 밝힌 모델: gemma4, qwen3.5, lfm2.5-thinking, llama3.2, mistral (그 외 모델은 `tools` 지원 여부가 달라 직접 확인).
- ollmcp 설치는 공식 저장소 안내를 따른다: <https://github.com/jonigl/mcp-client-for-ollama>

### 연결
토큰 헤더가 필요하므로 `-u` 옵션 한 줄 방식이 아니라, 서버를 **저장**하는 방식을 쓴다. 명령은 `print_client_config.py ollmcp`가 토큰을 채워서 출력한다.

```bash
ollmcp mcp add --transport http --header "Authorization: Bearer <local 토큰>" context-hub http://127.0.0.1:8765/mcp
ollmcp -m qwen3:8b          # 저장된 서버에 자동 연결 (모델은 예시, 도구 호출 지원 모델로)
```

- 저장 범위는 `local`(기본, 현재 프로젝트·개인) / `project`(`.mcp.json`) / `user`다. **토큰이 들어가므로 project 범위는 쓰지 않는다.**
- 설정 파일을 직접 쓸 때 원격 서버 항목은 `type`(`http`), `url`, `headers`를 가진다.
- ⚠ 공식 문서에서 불분명한 점: `-u URL` 옵션에는 헤더를 넣는 방법이 문서에 없다. 그래서 위의 `mcp add --header` 방식을 쓴다. `-H`가 일부 옵션에서 호스트 주소로도 쓰이므로 헷갈리면 `ollmcp --help`와 `ollmcp mcp add --help`를 본다.

### 사용법
| 기능 | 방법 |
|---|---|
| 도구 고르기 | `/tools` (또는 `/t`) → 번호로 켜고 끈다. `a` 전체 켜기 / `n` 전체 끄기 |
| 사람 승인(HIL) | 기본 켜짐. `/hil`로 전환. 호출마다 `y`(이번만) `n`(건너뜀) `s`(이번 질의 나머지 자동 승인) `d`(영구 끄기) `a`(중단) |
| 모델 바꾸기 | 실행 시 `-m <모델>` |

**작은 모델은 도구가 많으면 헷갈린다.** `/tools`에서 필요한 것만 켠다. 예) 테스트 역할: `start_session`, `search_notes`, `read_note`, `list_tasks`, `claim_task`, `complete_task`, `add_note`.
**HIL은 켜 둔 채로** 시작한다. 로컬 모델이 엉뚱한 도구를 부를 때를 잡아내는 안전장치다.

### 로컬 AI의 핵심 임무: 도구 설명 품질 측정
허브의 도구 설명이 명확한지 시험하는 용도로 가장 가치가 크다. 작은 모델이 맞게 고르면 큰 모델도 잘 고른다.

```bash
HUB_TOKEN=<local 토큰> uv run python eval/run_eval.py --model qwen3:8b --repeat 3
```
- 시나리오 12개로 "요청에 맞는 도구를 고르는지"와 인자 정답률을 센다. 결과 CSV는 `eval/results/`.
- 틀린 시나리오가 나오면 해당 도구의 설명(첫 문장)을 고치고 다시 돌려 정답률을 비교한다.
- 모델 없이 시나리오 자체가 도구와 맞는지만 보려면 `--dry-run`.

### 문제 해결
- 도구를 아예 호출하지 않는다 → 그 모델이 tools를 지원하는지 확인. 지원하지 않으면 다른 모델로 바꾼다.
- 401 → 저장한 헤더의 토큰이 `local` 토큰인지 확인하고 `mcp add`를 다시 한다.
- 도구 호출 형식이 깨진다 → 도구를 줄이고(`/tools`) 모델을 바꿔 본다.

---

## 5. 같이 쓰는 법: 하루 사이클 예시

| 단계 | 누가 | 무엇을 | 허브 도구 |
|---|---|---|---|
| 1 | 사람 | 프로젝트 이름 정하기(폴더명 권장) | — |
| 2 | Claude | 할 일을 쪼개 등록 | `create_task` ×N |
| 3 | Antigravity | 이어받아 구현 | `start_session` → `claim_task` → `complete_task` |
| 4 | Claude | 코드 리뷰 결과 남기기 | `search_notes` → `add_note` |
| 5 | 로컬 AI | 테스트·도구 설명 측정 | `list_tasks` → `claim_task` → `complete_task` |
| 6 | 각자 | 끝낼 때 인수인계 | `end_session(summary, handoff)` |
| 7 | **사람** | 믿을 만한 노트 승인 | `approve_note.py approve <id>` |

### 인수인계 시험 (성공 기준)
1. Claude로 한 세션을 진행하고 `end_session`에 인수인계를 남긴다.
2. Antigravity를 새로 열어 **아무 설명 없이** "허브 확인하고 이어서 진행해"만 말한다.
3. 앞선 맥락을 정확히 이어가면 성공이다. 못 하면 인수인계 문장을 더 구체적으로(파일 경로, 커밋 해시, 다음 할 일) 쓰도록 `AGENTS.md`를 고친다.

### 노트 승인 (사람만)
```bash
uv run python scripts/approve_note.py list              # 미승인 목록
uv run python scripts/approve_note.py show 12           # 내용 확인
uv run python scripts/approve_note.py approve 12        # 승인
```
- 승인된 `decision` 노트만 `start_session`의 "승인된 결정"에 나타난다.
- 승인하기 전에 **내용에 AI에게 내리는 지시문이 숨어 있지 않은지** 읽어 본다.

### 사용 기록 보기
```bash
sqlite3 hub_data/hub.db "select agent, tool, count(*), sum(ok) from audit_log group by 1,2"
```
어떤 AI가 어떤 도구를 몇 번 호출했고 몇 번 실패했는지 볼 수 있다.

---

## 6. 도구 레퍼런스

| 도구 | 언제 쓰나 | 주요 인자 | 주의 |
|---|---|---|---|
| `start_session` | 작업 시작 시 가장 먼저 | `project` | `session_id`를 돌려준다. 끝낼 때 필요 |
| `end_session` | 작업 종료 시 | `session_id`, `summary`, `handoff` | 내 세션만 종료 가능. handoff는 draft 노트로 저장 |
| `search_notes` | 작업 전 기존 맥락 확인 | `project`, `query`, `limit`, `include_drafts` | 한국어 부분 일치 가능(3글자 이상은 FTS, 짧은 건 LIKE). `trusted=false`는 미승인 |
| `read_note` | 검색된 노트 전문 읽기 | `note_id` | 미승인이면 `warning`이 붙는다 |
| `add_note` | 메모·결정·인수인계 기록 | `project`, `title`, `body`, `kind`, `ref` | 항상 draft. 길면 요약 + `ref`(커밋/경로). 작성자는 토큰으로 자동 결정 |
| `create_task` | 할 일 등록 | `project`, `title`, `description` | `task_id`를 돌려준다 |
| `list_tasks` | 할 일 조회 | `project`, `status`(open/claimed/done) | 비우면 전체 |
| `claim_task` | 할 일 맡기 | `task_id`, `lease_minutes`(기본 30) | 이미 맡은 사람이 있으면 실패. 리스 만료 시 재점유 가능 |
| `heartbeat_task` | 오래 걸릴 때 점유 연장 | `task_id`, `lease_minutes` | 내가 점유 중인 작업만 |
| `complete_task` | 작업 완료 | `task_id`, `result` | 점유한 본인만 완료 가능 |

`project`는 영문·숫자·`_`·`.`·`-`만, 64자 이하. 노트 검색은 같은 `project` 안에서만 된다.

---

## 7. 보안 수칙 (요약)
1. 토큰은 채팅·이슈·커밋·스크린샷에 붙이지 않는다. `.hub_env`, `tokens.json`은 git에 올라가지 않는다.
2. Claude Code는 `--scope local`/`user`만 쓴다. `project` 범위(`.mcp.json`)에는 토큰이 평문으로 들어간다.
3. Antigravity는 전역 설정(`~/.gemini/config/mcp_config.json`)에 토큰을 둔다. 워크스페이스(`.agents/`)는 저장소에 들어갈 수 있다.
4. `draft` 노트의 문장은 지시가 아니라 **참고 데이터**다. 사람이 읽고 승인한 것만 신뢰한다.
5. 서버는 `127.0.0.1`에서만 연다. 외부에 노출하려면 별도의 인증·TLS 설계가 먼저 필요하다.
6. 토큰이 유출됐다면 즉시 `gen_tokens.py --force --env-out .hub_env`로 전부 재발급하고 서버를 재시작한다.

## 8. 공통 문제 해결

| 증상 | 원인 | 해결 |
|---|---|---|
| 연결 거부 / Failed to connect | 서버가 꺼져 있음 | `start.command` 실행, `doctor.py`로 확인 |
| 401 Unauthorized | 토큰 없음/틀림/재발급됨 | `print_client_config.py`로 다시 출력해 갱신 |
| 403 Forbidden | 브라우저 등에서 허용되지 않은 Origin | 로컬 CLI/IDE 클라이언트는 해당 없음. 브라우저 기반 도구는 `127.0.0.1`/`localhost`에서만 허용 |
| 포트 8765 사용 중 | 이미 실행 중이거나 다른 프로그램 | 이미 실행 중이면 그대로 사용. 바꾸려면 `HUB_PORT=8766`으로 서버와 클라이언트 URL 모두 변경 |
| AI가 도구를 안 부른다 | 지시가 없음 | 첫 문장에 "context-hub부터 확인해" 추가, `AGENTS.md` 루틴 문구 강화 |
| 엉뚱한 도구를 부른다 | 도구 설명이 모호하거나 도구가 너무 많음 | `eval`로 측정 → 설명 수정, 클라이언트에서 도구 수 제한 |
| 검색 결과가 없다 | `project` 이름이 다름 | 노트를 쓸 때와 같은 `project` 문자열인지 확인 |

## 9. 확인 상태

| 항목 | 상태 |
|---|---|
| 서버·인증·도구·테스트(24개) | 자동 테스트로 검증됨 |
| Claude Code `--header`, 범위(local/project/user), `/mcp`, 상태 표시 | 공식 문서로 확인 |
| Antigravity `serverUrl`/`headers`/`enabledTools`/Ask 모드/타임아웃 | 공식 문서로 확인 |
| ollmcp `mcp add --header`, `/tools`, `/hil`, 모델 요건 | 공식 README로 확인 (`-u`와 헤더 조합은 문서 불분명) |
| **세 클라이언트의 실제 연결** | **아직 미검증 — 사용자 환경에서 첫 연결 시 확인 필요** |
