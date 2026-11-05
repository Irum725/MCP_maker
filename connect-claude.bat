@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if "%HUB_PORT%"=="" set "HUB_PORT=8765"
set "URL=http://127.0.0.1:%HUB_PORT%/mcp"

REM 등록 범위는 local(저장소 밖)이다. project 범위는 토큰이 .mcp.json에 평문으로 들어가 유출될 수 있어 쓰지 않는다.
where claude >nul 2>&1
if errorlevel 1 goto no_claude
where uv >nul 2>&1
if errorlevel 1 goto no_uv

if exist .hub_env goto have_env
echo 토큰 평문 파일(.hub_env)이 없습니다.
echo 새로 발급하면 기존 토큰은 모두 무효화되고, 실행 중인 서버를 껐다 켜야 합니다.
set "ANS="
set /p "ANS=새로 발급할까요? [y/N] "
if /i not "%ANS%"=="y" goto cancelled
uv run python scripts\gen_tokens.py --force --env-out .hub_env >nul
if errorlevel 1 goto fail_token
echo 재발급 완료. start.bat 으로 서버를 (다시) 시작하세요.

:have_env
set "TOK="
for /f "usebackq delims=" %%i in (`uv run python scripts\print_token.py claude`) do set "TOK=%%i"
if "%TOK%"=="" goto no_token

call claude mcp remove context-hub >nul 2>&1
call claude mcp add --transport http --scope local context-hub "%URL%" --header "Authorization: Bearer %TOK%"
if errorlevel 1 goto fail_add
echo.
call claude mcp list
echo.
echo 등록 완료. 이 폴더에서 Claude Code를 실행하면 context-hub 도구를 쓸 수 있습니다.
echo (서버는 start.bat 으로 켜 두어야 합니다)
goto end

:no_claude
echo claude 명령을 찾을 수 없습니다. Claude Code가 설치되어 있는지 확인하세요.
goto end
:no_uv
echo uv가 설치되어 있지 않습니다. 설치: winget install --id=astral-sh.uv -e
goto end
:no_token
echo .hub_env에서 claude 토큰을 찾지 못했습니다.
goto end
:fail_token
echo 토큰 발급에 실패했습니다.
goto end
:fail_add
echo 등록에 실패했습니다.
goto end
:cancelled
echo 취소했습니다.

:end
echo.
pause
endlocal
