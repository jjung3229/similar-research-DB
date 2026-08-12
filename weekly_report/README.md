# weekly_report — 주간보고 초안 자동 작성

한 주 동안 PC에서 실제로 한 일의 흔적을 모아, 금요일에 명령 한 번으로 **근거가 붙은
주간보고 초안**을 만든다.

수집하는 것은 네 가지다.

| 소스 | 무엇을 알 수 있나 |
|---|---|
| 활성 창 제목 + 사용 시간 | 어떤 문서·과제를 언제 얼마나 다뤘는지 |
| Outlook 보낸메일 / 받은메일 / 회의 일정 | 무엇을 보고·협의했는지, 회의에 얼마나 썼는지 |
| 그 주에 수정된 문서 | 실제로 만들어낸 산출물 |
| git 커밋 | 개발 실적 (가장 신뢰도 높음) |

화면을 녹화하거나 캡처하지 않는다. 키 입력 내용도 읽지 않는다.

## 왜 창 제목만으로 되나

창 제목에는 이미 파일명·메일제목·탭제목이 들어 있다.

```
AXDX_로드맵_v3.pptx - PowerPoint          →  로드맵 문서 작업
ontology_axdx.py - repo - Visual Studio Code  →  온톨로지 코드 작업
RE: ROM 검증 결과 회신 - 메시지(HTML)      →  해당 건 메일 처리
```

다만 창 제목만으로는 **"열어놨다"와 "작업했다"를 구분할 수 없다.** 그래서 신호를
교차시켜 판정한다.

| 신호 조합 | 판정 |
|---|---|
| 창 제목의 파일명 == 그 주 수정된 파일, 수정시각이 세션 안 | **작성·수정** (확정) |
| 창 세션만 있고 파일 수정 없음 | **검토·열람** (실적으로 단정하지 않음) |
| Outlook 회의 일정 | **회의 참석** |
| 보낸 메일 | **보고·발송** |
| git 커밋 | **개발** |
| 3분 이상 무입력 | 시간 집계 중단 (자리비움) |

## 설치

파이썬 3.9 이상이면 **추가 설치 없이 동작한다.**

```
pip install PyYAML          # 선택. 없으면 config.json 사용
pip install pywin32         # 선택. Outlook 메일·일정 수집 시에만 필요
```

## 설정

`config.example.yaml` 을 같은 폴더에 `config.yaml` 로 복사하고 고친다.
(PyYAML 설치가 어려우면 같은 내용을 `config.json` 으로 저장해도 된다.)

최소한 이 세 가지는 채워야 한다.

```yaml
user:
  name: "홍길동"
  email: "hong@example.com"     # git 커밋 author 필터

files:
  watch_dirs:                    # 공유 드라이브 전체를 넣지 말 것 (느려진다)
    - "C:/Users/사용자명/Documents"

projects:                        # 활동을 과제로 묶는 규칙
  - name: "AX/DX 추진 로드맵"
    match: ["axdx", "로드맵", "온톨로지"]
```

`projects` 는 처음엔 비워두고, 보고서 아래 **"분류되지 않은 활동"** 을 보며 채워
나가는 편이 빠르다.

## 사용법

**1) 창 기록기를 상시 실행한다** (한 번만 등록하면 된다)

```
python -m weekly_report track
```

콘솔 창 없이 자동으로 띄우려면 `scripts/track_silent.vbs` 안의 경로를 고친 뒤,
그 바로가기를 시작 프로그램 폴더(`Win+R` → `shell:startup`)에 넣는다.

**2) 금요일에 보고서를 만든다**

```
python -m weekly_report run --week this
```

`scripts/weekly.bat` 의 경로를 고쳐두면 더블클릭으로 실행할 수 있다.

결과는 `data_dir/report/` 에 세 개가 생긴다.

| 파일 | 내용 |
|---|---|
| `weekly_2026-W33.md` | **주간보고 초안** (이것을 다듬어 제출) |
| `evidence_2026-W33.json` | 근거 전체. 초안이 이상할 때 확인 |
| `payload_2026-W33.json` | LLM 으로 나간 내용 (`--dry-run` 일 때만) |

### 그 밖의 명령

```
python -m weekly_report collect --week last     # 수집만
python -m weekly_report report  --week last     # 보고서만
python -m weekly_report report  --dry-run       # LLM 호출 없이 내용만 확인
python -m weekly_report llm-check               # 사내 LLM 연결 확인
python -m weekly_report import-mail 보낸메일.csv  # Outlook 이 막혔을 때
```

`--week` 은 `this` / `last` / `2026-W33` / `2026-08-12` 를 받는다.

## 사내 LLM 연결

문장 다듬기를 LLM에 맡기려면 사내 엔드포인트를 설정한다. **외부(인터넷) LLM 은 쓰지
않는다.**

```yaml
llm:
  enabled: true
  api_style: "openai"                 # 대부분의 사내 포털이 이 형식
  base_url: "http://사내LLM주소/v1"
  model: "사내모델명"
  api_key_env: "INHOUSE_LLM_API_KEY"  # 키가 필요 없으면 빈 문자열
  bypass_proxy: true                  # 사내 주소는 프록시를 타지 않게
```

연결 확인:

```
python -m weekly_report llm-check
```

사내 규격이 OpenAI 호환이 아니면 `api_style: custom` 으로 두고 요청 형식과 응답
경로를 직접 적는다.

```yaml
llm:
  api_style: "custom"
  base_url: "http://사내LLM주소/api/generate"
  request_template:
    prompt: "{{SYSTEM}}\n\n{{PROMPT}}"
    max_new_tokens: 4000
  response_path: "result.text"
```

**LLM 이 꺼져 있거나 호출이 실패해도 보고서는 나온다.** 이 경우 수집된 사실을 정리한
규칙 기반 초안으로 대체하고, 그 사실을 화면에 알린다. LLM 은 문장을 다듬는 역할일 뿐
이 도구의 본체가 아니다.

## 보안

- 수집 원본은 `data_dir` 아래 **로컬에만** 저장된다. 한 줄에 기록 하나인 텍스트 파일
  이라 메모장으로 열어 직접 지울 수 있다.
- 사내 LLM 으로 나가는 내용도 마스킹을 거친다. 주민번호·카드번호·전화번호·이메일
  주소·API 키 형태의 문자열은 자동으로 가려진다.
- `redact.drop_keywords` 에 적은 단어(예: `대외비`)가 들어간 기록은 **통째로 제외**된다.
- `activity.ignore_titles` 에 적은 단어가 창 제목에 있으면 애초에 기록하지 않는다.
- 무엇이 나가는지 먼저 보고 싶으면 `--dry-run` 으로 `payload_*.json` 을 확인한다.

## 알아둘 점

- **창 제목 조회는 키로깅이 아니라 표준 Win32 조회 API**를 쓴다. 다만 상시 상주
  프로그램이므로 사내 규정상 문제가 없는지는 확인이 필요하다.
- **Outlook COM 접근이 사내 정책으로 막힐 수 있다.** 그 경우 메일 수집만 자동으로
  건너뛰고 나머지는 정상 동작한다. 대안으로 Outlook에서 보낸편지함을 CSV로 내보낸 뒤
  `import-mail` 로 넣을 수 있다.
- **파일 수정시각(mtime)은 열었다 저장만 해도 갱신된다.** 그래서 창 사용시간과 교차
  검증한다.
- **회의·구두 협의·출장은 Outlook 일정에 있어야 잡힌다.** 일정에 없으면 누락된다.
- 보고서 맨 아래에 수집되지 않은 소스를 표시하므로, 누락 가능성을 항상 확인할 수 있다.

## 검증

```
python weekly_report/tests/test_offline.py
```

가상의 한 주 데이터로 마스킹·집계·교차검증·보고서 생성을 전부 확인한다 (45개 항목).
Windows·Outlook 없이도 실행된다.

실제 PC에서는 이 순서로 확인하는 것을 권한다.

1. `track` 을 10분쯤 실행한 뒤 `data_dir/activity/` 에 기록이 쌓이는지 확인
2. `collect --week this` 로 메일·문서·커밋 건수 확인
3. `report --dry-run` 으로 `evidence_*.json` 내용이 사실과 맞는지 확인
4. `llm-check` 후 `report` 로 초안 생성
