@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
if "%HUB_PORT%"=="" set "HUB_PORT=8765"

where uv >nul 2>&1
if errorlevel 1 goto no_uv

echo [1/3] 환경 준비 (uv sync)
uv sync -q
if errorlevel 1 goto fail_sync

if exist tokens.json goto have_tokens
echo [2/3] 첫 실행: 에이전트 토큰 발급
uv run python scripts\gen_tokens.py --env-out .hub_env >nul
if errorlevel 1 goto fail_token
echo   토큰을 .hub_env에 저장했습니다 (git 제외).
echo   이어서 connect-claude.bat 을 더블클릭하면 Claude Code에 연결됩니다.
goto check_port
:have_tokens
echo [2/3] 토큰 있음 (건너뜀)

:check_port
netstat -ano | findstr /R /C:":%HUB_PORT% .*LISTENING" >nul
if not errorlevel 1 goto already

echo [3/3] 서버 시작 - 종료하려면 Ctrl+C (창을 닫아도 종료됩니다)
uv run python -m context_hub.server
echo 서버가 종료되었습니다.
goto end

:already
echo 이미 포트 %HUB_PORT% 에서 서버가 실행 중입니다. 이 창은 닫아도 됩니다.
goto end

:no_uv
echo uv가 설치되어 있지 않습니다.
echo 설치: winget install --id=astral-sh.uv -e
goto end

:fail_sync
echo 환경 준비에 실패했습니다.
goto end

:fail_token
echo 토큰 발급에 실패했습니다.

:end
echo.
pause
endlocal
