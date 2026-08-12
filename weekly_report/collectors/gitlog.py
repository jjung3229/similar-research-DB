"""git 커밋 수집기.

설정된 폴더 아래에서 저장소를 찾아 로컬 `.git` 만 읽는다. 원격 서버에 접속하지 않는다.
"""

from __future__ import annotations

import subprocess
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterator

SEP = "\x1f"      # 필드 구분자 (커밋 메시지에 나올 일이 없는 문자)
REC = "\x1e"      # 레코드 구분자


def find_repos(roots: list[str], max_depth: int = 3) -> list[Path]:
    found: list[Path] = []
    for root in roots:
        base = Path(root).expanduser()
        if not base.exists():
            continue
        if (base / ".git").exists():
            found.append(base)
            continue
        for depth in range(1, max_depth + 1):
            pattern = "/".join(["*"] * depth) + "/.git"
            for git_dir in base.glob(pattern):
                repo = git_dir.parent
                if repo not in found:
                    found.append(repo)
    return found


def collect(cfg: dict, start: date, end: date) -> Iterator[dict[str, Any]]:
    gcfg = cfg["git"]
    if not gcfg.get("enabled", True):
        return
    author = cfg["user"].get("email") or cfg["user"].get("name") or ""
    since = start.isoformat()
    until = (end + timedelta(days=1)).isoformat()

    for repo in find_repos(gcfg.get("repo_roots", []), int(gcfg.get("max_depth", 3))):
        cmd = [
            "git", "-C", str(repo), "log",
            f"--since={since}", f"--until={until}",
            f"--pretty=format:{REC}%H{SEP}%aI{SEP}%an{SEP}%s",
            "--numstat", "--no-merges",
        ]
        if author:
            cmd.insert(4, f"--author={author}")
        try:
            out = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60
            ).stdout
        except Exception:
            continue

        for chunk in out.split(REC):
            chunk = chunk.strip("\n")
            if not chunk:
                continue
            head, _, body = chunk.partition("\n")
            parts = head.split(SEP)
            if len(parts) < 4:
                continue
            sha, when, name, subject = parts[0], parts[1], parts[2], parts[3]

            files, added, removed = [], 0, 0
            for line in body.splitlines():
                cols = line.split("\t")
                if len(cols) != 3:
                    continue
                files.append(cols[2])
                added += int(cols[0]) if cols[0].isdigit() else 0
                removed += int(cols[1]) if cols[1].isdigit() else 0

            yield {
                "kind": "commit",
                "time": when,
                "repo": repo.name,
                "sha": sha[:8],
                "author": name,
                "subject": subject,
                "files": files[:20],
                "files_changed": len(files),
                "added": added,
                "removed": removed,
            }
