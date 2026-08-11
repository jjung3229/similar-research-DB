#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""단독 실행 HTML 만들기.

pdf.js, SheetJS, 추출 로직, 화면 코드를 파일 하나로 합친다. 만들어진 HTML은
설치도 인터넷도 없이 브라우저에서 그냥 열면 되는 변환기가 된다.

    npm install          # 처음 한 번 (pdfjs-dist, xlsx-js-style)
    python build.py      # ../토지세목조서_변환기.html 생성
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODULES = os.path.join(HERE, "node_modules")

#: (템플릿 자리표시자, 넣을 파일)
PARTS = [
    ("<!--PDFJS-->", os.path.join(MODULES, "pdfjs-dist/legacy/build/pdf.min.js")),
    ("<!--XLSX-->", os.path.join(MODULES, "xlsx-js-style/dist/xlsx.min.js")),
    ("<!--CORE-->", os.path.join(HERE, "core.js")),
    ("<!--EXCEL-->", os.path.join(HERE, "excel.js")),
    # 해석기(worker)를 같은 창에서 실행해 둔다. 그러면 pdf.js 가 별도 파일을 받아오지
    # 않고 이것을 그대로 쓴다 — 파일을 그냥 열어도(file://) 브라우저를 가리지 않는다.
    ("<!--WORKER-->", os.path.join(MODULES, "pdfjs-dist/legacy/build/pdf.worker.min.js")),
    ("<!--APP-->", os.path.join(HERE, "app.js")),
]

OUTPUT = os.path.join(os.path.dirname(HERE), "토지세목조서_변환기.html")


def read(path: str) -> str:
    if not os.path.exists(path):
        sys.exit(f"파일이 없습니다: {path}\n먼저 이 폴더에서 'npm install' 을 실행하세요.")
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def main() -> int:
    html = read(os.path.join(HERE, "index.template.html"))

    for marker, path in PARTS:
        source = read(path)
        # </script> 가 소스 안에 있으면 HTML 이 중간에 끊긴다. 실제로는 없지만 확인한다.
        if "</script" in source.lower():
            sys.exit(f"{os.path.basename(path)} 안에 </script 가 있어 그대로 넣을 수 없습니다.")
        block = f"<script>\n{source}\n</script>"
        html = html.replace(marker, block)

    with open(OUTPUT, "w", encoding="utf-8") as fh:
        fh.write(html)

    size = os.path.getsize(OUTPUT) / (1024 * 1024)
    print(f"만들었습니다: {OUTPUT}  ({size:.1f}MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
