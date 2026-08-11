#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""토지세목조서 PDF → 엑셀 변환기 (웹 화면).

터미널이 익숙하지 않아도 쓸 수 있게, PDF를 끌어다 놓으면 엑셀을 내려받는
간단한 화면을 띄운다. 파이썬 기본 기능만 쓰기 때문에 별도 웹 프레임워크는
설치하지 않아도 된다.

실행:
    python app.py            # 브라우저가 자동으로 열린다
    python app.py --port 9000 --no-browser
"""

from __future__ import annotations

import argparse
import email
import html
import io
import json
import os
import shutil
import tempfile
import threading
import traceback
import uuid
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, List, Tuple
from urllib.parse import unquote

import land_schedule

MAX_UPLOAD = 200 * 1024 * 1024  # 200MB

WORKDIR = tempfile.mkdtemp(prefix="land-schedule-")
RESULTS: Dict[str, Tuple[str, str]] = {}  # 토큰 -> (파일경로, 내려받을 이름)
LOCK = threading.Lock()


PAGE = """<!doctype html>
<html lang="ko">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>토지세목조서 PDF → 엑셀 변환</title>
<style>
  :root { color-scheme: light dark; }
  * { box-sizing: border-box; }
  body { margin: 0; padding: 40px 20px; font-family: -apple-system, "Apple SD Gothic Neo",
         "Malgun Gothic", "Noto Sans KR", sans-serif; background: #f5f6f8; color: #1b1f23; }
  @media (prefers-color-scheme: dark) { body { background: #16181d; color: #e8eaed; } }
  .wrap { max-width: 760px; margin: 0 auto; }
  h1 { font-size: 22px; margin: 0 0 6px; }
  p.sub { margin: 0 0 24px; color: #6b7280; font-size: 14px; line-height: 1.6; }
  #drop { border: 2px dashed #9aa4b2; border-radius: 14px; padding: 54px 20px; text-align: center;
          background: rgba(127,127,127,.05); cursor: pointer; transition: .15s; }
  #drop.hot { border-color: #1f6feb; background: rgba(31,111,235,.10); }
  #drop strong { display: block; font-size: 17px; margin-bottom: 6px; }
  #drop span { color: #6b7280; font-size: 13px; }
  input[type=file] { display: none; }
  .card { margin-top: 18px; padding: 16px 18px; border-radius: 12px; background: rgba(127,127,127,.08);
          font-size: 14px; line-height: 1.7; }
  .card h3 { margin: 0 0 8px; font-size: 15px; }
  .ok { color: #1a7f37; } .warn { color: #b26a00; } .err { color: #c0392b; }
  a.dl { display: inline-block; margin-top: 10px; padding: 9px 16px; border-radius: 8px;
         background: #1f6feb; color: #fff; text-decoration: none; font-size: 14px; }
  ul { margin: 6px 0 0; padding-left: 18px; } li { margin: 2px 0; }
  .muted { color: #6b7280; font-size: 13px; }
</style>
<div class="wrap">
  <h1>수용할 또는 사용할 토지세목조서 → 엑셀</h1>
  <p class="sub">고시문 PDF를 아래 상자에 끌어다 놓으면 토지세목조서 표를 찾아 엑셀로 바꿔 드립니다.
     여러 개를 한꺼번에 올려도 됩니다. 파일은 이 컴퓨터 안에서만 처리되고 어디로도 전송되지 않습니다.</p>

  <label id="drop" for="file">
    <strong>PDF를 여기에 끌어다 놓으세요</strong>
    <span>또는 눌러서 파일 선택</span>
    <input id="file" type="file" accept="application/pdf,.pdf" multiple>
  </label>

  <div id="out"></div>
</div>
<script>
const drop = document.getElementById('drop');
const file = document.getElementById('file');
const out  = document.getElementById('out');

['dragenter','dragover'].forEach(e => drop.addEventListener(e, ev => {
  ev.preventDefault(); drop.classList.add('hot');
}));
['dragleave','drop'].forEach(e => drop.addEventListener(e, ev => {
  ev.preventDefault(); drop.classList.remove('hot');
}));
drop.addEventListener('drop', ev => send(ev.dataTransfer.files));
file.addEventListener('change', () => send(file.files));

function esc(s) { return String(s).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])); }

async function send(files) {
  if (!files || !files.length) return;
  out.innerHTML = '';
  for (const f of files) {
    const card = document.createElement('div');
    card.className = 'card';
    card.innerHTML = '<h3>' + esc(f.name) + '</h3><div class="muted">변환 중… 쪽수가 많으면 30초 정도 걸립니다.</div>';
    out.appendChild(card);

    const fd = new FormData();
    fd.append('file', f, f.name);
    try {
      const res = await fetch('/convert', { method: 'POST', body: fd });
      const data = await res.json();
      card.innerHTML = '<h3>' + esc(f.name) + '</h3>' + render(data);
    } catch (err) {
      card.innerHTML = '<h3>' + esc(f.name) + '</h3><div class="err">변환에 실패했습니다: ' + esc(err) + '</div>';
    }
  }
}

function render(d) {
  if (d.error) return '<div class="err">' + esc(d.error) + '</div>';
  let h = '<div>자료 <b>' + d.records.toLocaleString() + '건</b> · 소계 ' + d.subtotals +
          '행 · 표가 있는 쪽 ' + d.pages_with_table + ' / 전체 ' + d.total_pages + '쪽</div>';
  if (d.checks) {
    h += d.mismatches === 0
      ? '<div class="ok">소계 검증: ' + d.checks + '개 구간 모두 일치 (누락 없음)</div>'
      : '<div class="warn">소계 검증: ' + d.checks + '개 구간 중 ' + d.mismatches +
        '개가 고시문 소계와 다릅니다. 엑셀 「검증」 시트에서 확인하세요.</div>';
  }
  if (d.warnings && d.warnings.length) {
    h += '<div class="warn">확인이 필요한 부분 ' + d.warnings.length + '건<ul>' +
         d.warnings.slice(0, 5).map(w => '<li>' + esc(w) + '</li>').join('') + '</ul></div>';
  }
  h += '<a class="dl" href="/download/' + d.token + '">엑셀 내려받기</a>';
  return h;
}
</script>
</html>
"""


def _parse_upload(content_type: str, body: bytes) -> List[Tuple[str, bytes]]:
    """multipart/form-data 본문에서 (파일이름, 내용) 목록을 뽑는다."""
    raw = b"Content-Type: " + content_type.encode() + b"\r\nMIME-Version: 1.0\r\n\r\n" + body
    message = email.message_from_bytes(raw)
    files: List[Tuple[str, bytes]] = []
    for part in message.walk():
        filename = part.get_filename()
        if not filename:
            continue
        payload = part.get_payload(decode=True)
        if payload:
            files.append((os.path.basename(filename), payload))
    return files


class Handler(BaseHTTPRequestHandler):
    server_version = "LandSchedule/1.0"

    def log_message(self, fmt: str, *args) -> None:  # 조용히
        pass

    # -- 응답 도우미 -------------------------------------------------------
    def _send(self, code: int, ctype: str, payload: bytes, extra: Dict[str, str] | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(payload)

    def _json(self, code: int, data: Dict) -> None:
        self._send(code, "application/json; charset=utf-8",
                   json.dumps(data, ensure_ascii=False).encode("utf-8"))

    # -- 라우팅 ------------------------------------------------------------
    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", PAGE.encode("utf-8"))
            return

        if self.path.startswith("/download/"):
            token = unquote(self.path[len("/download/"):])
            with LOCK:
                entry = RESULTS.get(token)
            if not entry:
                self._send(404, "text/plain; charset=utf-8", "만료된 링크입니다.".encode("utf-8"))
                return
            path, name = entry
            with open(path, "rb") as fh:
                data = fh.read()
            quoted = "".join(f"%{b:02X}" for b in name.encode("utf-8"))
            self._send(
                200,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                data,
                {"Content-Disposition": f"attachment; filename*=UTF-8''{quoted}"},
            )
            return

        self._send(404, "text/plain; charset=utf-8", "없는 주소입니다.".encode("utf-8"))

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/convert":
            self._json(404, {"error": "없는 주소입니다."})
            return

        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            self._json(400, {"error": "파일이 비어 있습니다."})
            return
        if length > MAX_UPLOAD:
            self._json(413, {"error": f"파일이 너무 큽니다({length // (1024*1024)}MB)."})
            return

        body = self.rfile.read(length)
        try:
            uploads = _parse_upload(self.headers.get("Content-Type", ""), body)
        except Exception:  # noqa: BLE001
            self._json(400, {"error": "업로드 내용을 읽지 못했습니다."})
            return

        if not uploads:
            self._json(400, {"error": "PDF 파일을 찾지 못했습니다."})
            return

        name, data = uploads[0]
        stem = os.path.splitext(name)[0] or "토지세목조서"
        pdf_path = os.path.join(WORKDIR, f"{uuid.uuid4().hex}.pdf")
        with open(pdf_path, "wb") as fh:
            fh.write(data)

        xlsx_path = os.path.splitext(pdf_path)[0] + ".xlsx"
        try:
            result = land_schedule.extract(pdf_path)
            info = land_schedule.to_excel(result, xlsx_path, source_name=name)
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            self._json(200, {"error": str(exc)})
            return
        finally:
            os.remove(pdf_path)

        token = uuid.uuid4().hex
        with LOCK:
            RESULTS[token] = (xlsx_path, f"{stem}.xlsx")

        self._json(200, {
            "token": token,
            "records": info["자료 건수"],
            "subtotals": info["소계 행"],
            "pages_with_table": info["표가 있는 페이지"],
            "total_pages": info["총 페이지"],
            "checks": info["검증 구간"],
            "mismatches": info["소계 불일치"],
            "warnings": info["경고"],
        })


def main() -> int:
    parser = argparse.ArgumentParser(description="토지세목조서 PDF → 엑셀 변환 웹 화면")
    parser.add_argument("--port", type=int, default=8765, help="사용할 포트 (기본 8765)")
    parser.add_argument("--host", default="127.0.0.1", help="바인딩 주소 (기본 127.0.0.1)")
    parser.add_argument("--no-browser", action="store_true", help="브라우저를 자동으로 열지 않음")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    url = f"http://{args.host}:{args.port}/"
    print(f"토지세목조서 변환기가 열렸습니다 → {url}")
    print("종료하려면 Ctrl+C 를 누르세요.")
    if not args.no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n종료합니다.")
    finally:
        server.server_close()
        shutil.rmtree(WORKDIR, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
