"""수정된 문서 수집기.

지정된 폴더에서 그 주에 수정 시각이 바뀐 파일을 찾는다. **파일을 열지 않고**
이름·수정시각·확장자·크기만 기록한다.

공유 드라이브 전체를 훑으면 느리므로 폴더 지정, 깊이 제한, 확장자 필터가 필수다.
"""

from __future__ import annotations

import os
from datetime import date, datetime, time as dtime, timedelta
from pathlib import Path
from typing import Any, Iterator


def collect(cfg: dict, start: date, end: date) -> Iterator[dict[str, Any]]:
    fcfg = cfg["files"]
    if not fcfg.get("enabled", True):
        return

    extensions = {e.lower() for e in fcfg.get("extensions", [])}
    ignore_dirs = {d.lower() for d in fcfg.get("ignore_dirs", [])}
    max_files = int(fcfg.get("max_files", 200))
    max_depth = int(fcfg.get("max_depth", 6))

    begin_ts = datetime.combine(start, dtime.min).timestamp()
    end_ts = datetime.combine(end + timedelta(days=1), dtime.min).timestamp()

    hits: list[tuple[float, dict[str, Any]]] = []
    for raw_root in fcfg.get("watch_dirs", []):
        root = Path(raw_root).expanduser()
        if not root.exists():
            continue
        root_depth = len(root.parts)

        for dirpath, dirnames, filenames in os.walk(root, topdown=True):
            current = Path(dirpath)
            if len(current.parts) - root_depth >= max_depth:
                dirnames[:] = []
            # 숨김 폴더와 제외 폴더는 아예 내려가지 않는다 (속도)
            dirnames[:] = [
                d for d in dirnames
                if d.lower() not in ignore_dirs and not d.startswith((".", "~$"))
            ]

            for name in filenames:
                if name.startswith("~$"):        # Office 임시 파일
                    continue
                suffix = Path(name).suffix.lower()
                if extensions and suffix not in extensions:
                    continue
                path = current / name
                try:
                    stat = path.stat()
                except OSError:
                    continue
                if not (begin_ts <= stat.st_mtime < end_ts):
                    continue
                hits.append(
                    (
                        stat.st_mtime,
                        {
                            "kind": "file",
                            "time": datetime.fromtimestamp(stat.st_mtime).isoformat(
                                timespec="seconds"
                            ),
                            "name": name,
                            "stem": Path(name).stem,
                            "ext": suffix,
                            "dir": str(current),
                            "size": stat.st_size,
                        },
                    )
                )

    hits.sort(key=lambda pair: pair[0], reverse=True)
    for _, record in hits[:max_files]:
        yield record
