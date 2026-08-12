@echo off
REM 금요일에 이 파일을 더블클릭하면 이번 주 보고서 초안이 만들어진다.
REM 아래 REPO 경로를 이 저장소를 내려받은 위치로 바꿔주세요.

set REPO=C:\work\repos\similar-research-DB

cd /d "%REPO%"
python -m weekly_report run --week this
if errorlevel 1 (
    echo.
    echo [!] 실행 중 문제가 있었습니다. 위 메시지를 확인하세요.
)
echo.
pause
