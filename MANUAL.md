# AX/DX 다이어그램 생성 시스템 — 사용 매뉴얼

HD한국조선해양 미래기술연구원의 **AX/DX 추진 로드맵**을 시각화하는 Python 스크립트 모음입니다.
각 스크립트는 matplotlib으로 다이어그램(PNG)을 생성하며, 같은 전략 체계를 서로 다른 관점(흐름·순환·온톨로지·상세 연계 등)으로 표현합니다.

---

## 1. 시스템 개요

모든 다이어그램은 아래의 **4대 전략 체계**를 공통 소재로 합니다.

| 구분 | 전략 | 내용 |
|---|---|---|
| DX | 전략1. 데이터베이스 | 생산실적·연구데이터 축적, R&D hi-way 플랫폼, OCR·VLM 비정형 검색 |
| DX | 전략2. 시뮬레이션 가속화 | GPU CFD, SimSolid·FE 구조해석, JAX·ACMS 선박진동, 변형 예측·제어 |
| DX | 전략3. 디지털트윈 | 장비DT(AIP·LIB·압축기), AI CHS, 전기추진 LBTS, 암모니아 실증, USV, 생산공정 가상검증 |
| AX | 전략4. AI Researcher | 공통활용·연구소별 Agent, Agent 스토어, 오케스트레이션 프레임워크 |

핵심 흐름: **데이터 → 시뮬레이션 가속 → Surrogate·ROM 생성 → 디지털트윈**, 그리고 **Agent(전략4)가 전 과정을 횡단 적용**하며 성과가 데이터베이스로 **환류**되는 구조입니다.

---

## 2. 요구 사항 (실행 환경)

| 항목 | 내용 |
|---|---|
| Python | 3.x |
| 필수 패키지 | `matplotlib`, `numpy` (cycle/linkage/ontology에서 사용) |
| 한글 폰트 | 나눔고딕 — `/usr/share/fonts/truetype/nanum/NanumGothic.ttf`, `NanumGothicBold.ttf` |
| 디스플레이 | 불필요 (`Agg` 백엔드 사용 — 서버·헤드리스 환경에서 실행 가능) |

설치 예시 (Ubuntu/Debian):

```bash
pip install matplotlib numpy
sudo apt-get install fonts-nanum
```

> ⚠️ 나눔고딕 폰트가 해당 경로에 없으면 `fontManager.addfont()`에서 오류가 납니다.
> 폰트 경로가 다른 환경이라면 각 스크립트 상단의 폰트 경로를 수정하세요 (→ 6장 참고).

---

## 3. 실행 방법

각 스크립트는 독립 실행형입니다. 인자 없이 실행하면 같은 이름의 PNG를 저장하고 `saved`를 출력합니다.

```bash
python core_axdx.py      # → core_axdx.png
python cycle_axdx.py     # → cycle_axdx.png
python fan_axdx.py       # → fan_axdx.png
python rel_axdx.py       # → rel_axdx.png
python tech_axdx.py      # → tech_axdx.png
python pipeline_axdx.py  # → pipeline_axdx.png
python linkage_axdx.py   # → linkage_axdx.png
python ontology_axdx.py  # → ontology_axdx.png
```

전체 일괄 생성:

```bash
for f in *_axdx.py; do python "$f"; done
```

> ⚠️ 저장 경로가 `/home/user/similar-research-DB/…` 로 **절대경로 하드코딩**되어 있습니다.
> 다른 환경에서는 각 스크립트 마지막의 `plt.savefig(...)` 경로를 수정해야 합니다.

---

## 4. 스크립트별 안내 (어떤 걸 언제 쓰나)

단순 → 상세 순서로 정리했습니다.

### 4.1 `core_axdx.py` — 핵심 흐름 미니멀 버전
- **내용**: 데이터베이스 → 시뮬레이션 가속화 → Surrogate·ROM → 디지털트윈의 4단계 직선 흐름 + 하단 Agent 밴드
- **용도**: 한 장으로 개념만 빠르게 전달할 때 (경영진 보고 도입부 등)
- **크기**: 20×9 in

### 4.2 `cycle_axdx.py` — 순환 구조 + 중앙 허브
- **내용**: 데이터베이스·시뮬레이션·디지털트윈 3축이 원형으로 순환(학습 데이터 → Surrogate·ROM → 운영데이터 환류)하고, 중앙에 AI Researcher(Agent) 허브가 3축 모두에 연결
- **특징**: 흰색 라인아트 아이콘(DB 실린더, fast-forward, 트윈 박스, 네트워크) 포함
- **용도**: "순환·환류 구조"를 강조하고 싶을 때
- **크기**: 12.5×12 in (정방형에 가까움)

### 4.3 `fan_axdx.py` — 디지털트윈 중심 fan-in/out
- **내용**: 왼쪽 입력(전략1 DB, 전략2 Surrogate·ROM, 현장 IoT·센서) → 중앙 디지털트윈 → 오른쪽 성과(지능 제어, 최적 운전·운영, 빠른 검증·설계) + 하단 전략4 Agent 밴드
- **용도**: 디지털트윈의 **가치 흐름(입력→성과)** 관점 설명
- **크기**: 16×9.3 in

### 4.4 `rel_axdx.py` — 4대 전략 연계 관계도
- **내용**: 4개 전략 노드를 나란히 배치, DX/AX 영역 구분 컨테이너, 전략2→3 사이 Surrogate·ROM 뱃지, 전략3↔4의 활용/환류 양방향 화살표, Agent의 전 축 적용 점선 호
- **용도**: **전략 간 관계**를 요약 수준에서 보여줄 때
- **크기**: 18.5×10 in

### 4.5 `tech_axdx.py` — 기술 연계도 (기술 메커니즘 관점)
- **내용**: 상단에 전략1→2→[Surrogate·ROM 산출물 노드]→3 기술 흐름, ROM 자산화·저장 및 실측 환류 피드백, 하단에 Agent 계층(데이터/해석/디지털트윈 Agent + Agent 스토어)
- **용도**: Surrogate·ROM을 **핵심 산출물**로 강조하는 기술 관점 설명
- **크기**: 22×13 in

### 4.6 `pipeline_axdx.py` — 추진 파이프라인 (흐름도)
- **내용**: AS-IS→TO-BE 패러다임 배너, 4대 전략 상세 블록(세부 항목 불릿 포함), TO-BE 성과 블록(검증시간 8배 단축 등), 환류 루프, 하단 AWS 데이터 파이프라인(Device→IoT Core→MSK→Kafka Connect→S3→Glue→Redshift→Airflow→RDS + Redis·DynamoDB)
- **용도**: **전체 추진 체계 + 인프라**를 한 장에 담은 실무 보고용
- **크기**: 24×12.5 in

### 4.7 `linkage_axdx.py` — 연계 상세도 (세부 항목 단위)
- **내용**: 전략별 컬럼(4열)에 세부 노드 20개를 배치하고, 노드 간 **실제 연결 관계**(ROM 재사용, CFD→안전설계, 선급 검증체계, 환류 등 13개 엣지)를 표시. 하단 AWS 파이프라인, 범례, 미연계 항목 주석 포함
- **용도**: 세부 과제 단위의 연계를 검토·설명할 때 (가장 상세한 실선 연결도)
- **크기**: 26×15 in
- **데이터 구조**: `COLS`(컬럼) / `N`(노드) / `E`(엣지) 딕셔너리·리스트로 분리되어 있어 항목 추가·수정이 쉬움 (→ 6장 참고)

### 4.8 `ontology_axdx.py` — 추진 로드맵 온톨로지
- **내용**: 4대 전략 필러(원형 대형 노드) + 세부 도메인·기술·AWS 파이프라인 클래스(원형 소형 노드) 총 33개를 온톨로지 형식으로 표현. Object Property(실선 관계)와 SubClassOf(점선 계층)를 구분, AS-IS/TO-BE 배너와 범례 포함
- **용도**: 전체 요소·관계를 **지식 그래프 형태**로 조망할 때 (가장 정보량이 많음)
- **크기**: 23×15.5 in
- **데이터 구조**: `N`(노드) / `OBJ`(관계) / `SUB`(계층) 으로 분리

---

## 5. 공통 코드 구조

모든 스크립트가 같은 패턴을 따릅니다:

```python
# 1) 헤드리스 백엔드 + 한글 폰트 등록
matplotlib.use("Agg")
fm.fontManager.addfont("/usr/share/fonts/truetype/nanum/NanumGothic.ttf")
plt.rcParams["font.family"] = "NanumGothic"

# 2) 색상 팔레트 상수 정의
BLUE, GREEN, PURP = "#2a5b8c", "#2e7d4f", "#7b52ab"

# 3) figure 생성, 축 숨김, 좌표계 설정
fig, ax = plt.subplots(figsize=(W, H))
ax.set_axis_off(); ax.set_xlim(...); ax.set_ylim(...)

# 4) 그리기 헬퍼 함수 정의 (box / node / arrow / flow 등)
# 5) 데이터(노드·엣지) 정의 후 헬퍼 호출
# 6) 저장
plt.savefig(".../파일명.png", dpi=150, bbox_inches="tight")
```

### 공통 색상 팔레트

| 색상 | HEX | 의미 |
|---|---|---|
| 파랑 | `#2a5b8c` / `#1f4e79` | DX 전략 (전략1~3) |
| 초록 | `#2e7d4f` | AX 전략 (전략4, Agent) |
| 보라 | `#7b52ab` | Surrogate·ROM (핵심 산출물) |
| 주황 | `#d98324` | AWS 데이터 파이프라인 |
| 빨강 | `#c0504d` | 환류·피드백, TO-BE 성과 |

---

## 6. 수정(커스터마이징) 가이드

### 6.1 저장 경로 / 해상도 변경
각 스크립트 마지막 줄:
```python
plt.savefig("/home/user/similar-research-DB/xxx.png", dpi=150, bbox_inches="tight")
```
- 경로를 원하는 위치로 변경 (상대경로 `"xxx.png"` 도 가능)
- 고해상도가 필요하면 `dpi=300` 등으로 조정

### 6.2 폰트 변경
스크립트 상단:
```python
for f in ["NanumGothic.ttf","NanumGothicBold.ttf"]:
    fm.fontManager.addfont(f"/usr/share/fonts/truetype/nanum/{f}")
plt.rcParams["font.family"] = "NanumGothic"
```
다른 한글 폰트를 쓰려면 폰트 파일 경로와 `font.family` 이름을 함께 바꿉니다.

### 6.3 문구·항목 수정
- **단순 다이어그램** (core/fan/rel/tech/pipeline): `box(...)` / `block(...)` / `node(...)` 호출부의 문자열 인자를 직접 수정
- **linkage_axdx.py**: 
  - 노드 추가 → `N` 딕셔너리에 `"키":("컬럼",y좌표,"라벨")` 추가
  - 연결 추가 → `E` 리스트에 `("출발","도착","라벨",색,모드,휨,선스타일,라벨위치)` 추가
    - 모드: `"h"`(가로 연결), `"v"`(세로 연결), `"arc"`(상단 곡선)
    - 선스타일: `"-"`(실선), `"--"`(점선=환류)
- **ontology_axdx.py**:
  - 노드 추가 → `N`에 `"키":("라벨","패밀리","class",(x,y))` 추가 (패밀리: `db`/`sim`/`dt`/`ai`/`pipe`/`tech`)
  - 관계 추가 → `OBJ`(라벨 있는 실선 관계) 또는 `SUB`(점선 계층) 리스트에 추가

### 6.4 색상 변경
스크립트 상단의 색상 상수(`BLUE`, `DXC`, `AXC` 등)만 바꾸면 전체에 일괄 반영됩니다.

---

## 7. 자주 발생하는 문제 (FAQ)

| 증상 | 원인 / 해결 |
|---|---|
| `findfont` 경고, 한글이 □□로 표시 | 나눔고딕 미설치 → `sudo apt-get install fonts-nanum` 후 matplotlib 캐시 삭제 (`rm -rf ~/.cache/matplotlib`) |
| `FileNotFoundError: .../nanum/...ttf` | 폰트 경로 상이 → 상단 폰트 경로를 실제 경로로 수정 |
| 저장 실패 (`No such file or directory`) | `savefig` 절대경로가 환경에 없음 → 경로 수정 (6.1) |
| 화면에 아무것도 안 뜸 | 정상 동작 — `Agg` 백엔드는 화면 출력 없이 파일로만 저장 |
| 텍스트가 겹침 | figsize·좌표는 현재 문구 길이에 맞춰 수동 조정된 값 → 문구를 크게 바꿨다면 좌표/폰트 크기를 함께 조정 |

---

## 8. 파일 구성 요약

| 스크립트 | 출력 | 관점 | 상세도 |
|---|---|---|---|
| `core_axdx.py` | `core_axdx.png` | 핵심 흐름 (직선) | ★ |
| `cycle_axdx.py` | `cycle_axdx.png` | 순환 + 중앙 허브 | ★★ |
| `fan_axdx.py` | `fan_axdx.png` | DT 중심 입력→성과 | ★★ |
| `rel_axdx.py` | `rel_axdx.png` | 4전략 연계 관계 | ★★ |
| `tech_axdx.py` | `tech_axdx.png` | 기술 메커니즘 | ★★★ |
| `pipeline_axdx.py` | `pipeline_axdx.png` | 추진 체계 + AWS 인프라 | ★★★★ |
| `linkage_axdx.py` | `linkage_axdx.png` | 세부 항목 실연결 | ★★★★★ |
| `ontology_axdx.py` | `ontology_axdx.png` | 온톨로지 (지식 그래프) | ★★★★★ |
