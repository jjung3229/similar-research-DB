' 창 기록기를 콘솔 창 없이 백그라운드로 실행한다.
'
' 사용법: 이 파일의 바로가기를 시작 프로그램 폴더에 넣는다.
'   Win+R → shell:startup → 바로가기 붙여넣기
'
' 아래 REPO 경로를 이 저장소를 내려받은 위치로 바꿔주세요.

REPO = "C:\work\repos\similar-research-DB"

Set shell = CreateObject("WScript.Shell")
shell.CurrentDirectory = REPO
' 0 = 창 숨김, False = 종료를 기다리지 않음
shell.Run "pythonw -m weekly_report track", 0, False
