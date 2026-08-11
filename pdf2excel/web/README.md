# 단독 실행 변환기 만들기 (개발용)

`../토지세목조서_변환기.html` 을 만드는 소스입니다.
쓰기만 할 사람은 이 폴더를 볼 필요가 없습니다 — 만들어진 HTML 파일 하나만 있으면 됩니다.

## 만들기

```bash
npm install      # pdfjs-dist, xlsx-js-style (처음 한 번)
python3 build.py # ../토지세목조서_변환기.html 생성
```

pdf.js·SheetJS·추출 로직·화면 코드를 HTML 파일 하나로 합칩니다.
만들어진 파일은 인터넷 연결 없이 브라우저에서 그냥 열면 동작합니다.

## 구성

| 파일 | 하는 일 |
| --- | --- |
| `core.js` | PDF에서 표를 읽어내는 핵심. `../land_schedule.py` 와 같은 규칙 |
| `excel.js` | 결과를 엑셀 4개 시트로 만든다 |
| `app.js` | 끌어다 놓기 화면 동작 |
| `index.template.html` | 화면 뼈대와 스타일 |
| `build.py` | 위의 것들과 라이브러리를 한 파일로 합친다 |

## 시험

**파이썬판과 한 줄씩 대조** — 파이썬 쪽이 기준입니다.

```bash
python3 - <<'PY'
import json, sys; sys.path.insert(0, '..')
import land_schedule as ls
r = ls.extract('고시문.pdf')
json.dump(r.records,  open('/tmp/py_records.json','w'), ensure_ascii=False)
json.dump(r.subtotals, open('/tmp/py_subtotals.json','w'), ensure_ascii=False)
PY
node tools/compare.js 고시문.pdf /tmp/py_records.json /tmp/py_subtotals.json
```

**브라우저에서 실제로 열어 확인**

```bash
npm install -D playwright
node tools/browser-test.js 고시문.pdf
```

## 파이썬판과의 차이

계양~강화선 고시문(2,984건 × 13열 = 38,792칸)으로 대조한 결과입니다.

- 번호·소재지·지번·지목·지적·편입면적·비고 → **완전히 같음**
- 성명·주소·권리의 종류 → 14행에서 띄어쓰기가 다름 (38,792칸 중 74칸, 0.2%)

가려진 이름(`한*예`)은 PDF 안에서 `한 예` 를 찍고 그 틈에 `*` 를 겹쳐 찍는 식이라,
글자 사이를 어떻게 읽느냐에 따라 띄어쓰기가 갈립니다. 대체로 이쪽이 더 정확합니다
(`부평**협동조합` / 파이썬판 `부 평**협동조합`). 다만 `㈜` 를 `(주)` 로 읽고,
한 곳에서 숫자 한 자가 옆 칸으로 밀립니다(45쪽 `외5인`).

숫자와 표 구조는 어느 쪽이든 같으므로, 집계·검증 결과는 완전히 일치합니다.
