"""활성 창 제목 수집기.

15초마다 지금 보고 있는 창의 제목과 프로그램 이름을 확인한다. 같은 창을 계속 보고
있으면 메모리에만 들고 있다가, 창이 바뀌거나 10분이 지나면 한 줄로 기록한다.

    {"start": "...", "end": "...", "seconds": 1230, "app": "POWERPNT",
     "title": "AXDX_로드맵_v3.pptx - PowerPoint"}

화면 이미지는 저장하지 않는다. 키 입력 내용도 읽지 않는다. 마지막 입력 '시각'만
확인해서 3분 넘게 아무 입력이 없으면 자리비움으로 보고 시간 계산을 멈춘다.

Windows 는 ctypes 로 Win32 API 를 직접 호출하므로 추가 설치가 필요 없다.
macOS/Linux 는 개발·테스트용 폴백이다.
"""

from __future__ import annotations

import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

IS_WINDOWS = platform.system() == "Windows"


# --------------------------------------------------------------------------
# Windows
# --------------------------------------------------------------------------
def _windows_backend() -> tuple[Callable[[], tuple[str, str]], Callable[[], float]]:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

    # 49.7일마다 순환하는 GetTickCount 대신 64비트 버전을 쓴다.
    tick_count = getattr(kernel32, "GetTickCount64", kernel32.GetTickCount)
    tick_count.restype = ctypes.c_ulonglong

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    def active_window() -> tuple[str, str]:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return "", ""

        length = user32.GetWindowTextLengthW(hwnd)
        title = ""
        if length:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            title = buf.value

        app = ""
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value:
            handle = kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value
            )
            if handle:
                try:
                    buf = ctypes.create_unicode_buffer(512)
                    size = wintypes.DWORD(512)
                    if kernel32.QueryFullProcessImageNameW(
                        handle, 0, buf, ctypes.byref(size)
                    ):
                        app = Path(buf.value).stem
                finally:
                    kernel32.CloseHandle(handle)
        return app, title

    def idle_seconds() -> float:
        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(info)
        if not user32.GetLastInputInfo(ctypes.byref(info)):
            return 0.0
        # dwTime 은 32비트라 tick 과 폭이 다르다. 하위 32비트만 비교한다.
        elapsed_ms = (int(tick_count()) & 0xFFFFFFFF) - info.dwTime
        if elapsed_ms < 0:
            elapsed_ms += 1 << 32
        return elapsed_ms / 1000.0

    return active_window, idle_seconds


# --------------------------------------------------------------------------
# macOS / Linux (개발·테스트용)
# --------------------------------------------------------------------------
def _macos_backend():
    script = (
        'tell application "System Events"\n'
        "set frontApp to name of first application process whose frontmost is true\n"
        "set windowTitle to \"\"\n"
        "try\n"
        "set windowTitle to name of front window of application process frontApp\n"
        "end try\n"
        "return frontApp & \"\\n\" & windowTitle\n"
        "end tell"
    )

    def active_window() -> tuple[str, str]:
        try:
            out = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, text=True, timeout=5,
            ).stdout.splitlines()
        except Exception:
            return "", ""
        app = out[0].strip() if out else ""
        title = out[1].strip() if len(out) > 1 else ""
        return app, title

    return active_window, lambda: 0.0


def _linux_backend():
    def active_window() -> tuple[str, str]:
        try:
            title = subprocess.run(
                ["xdotool", "getactivewindow", "getwindowname"],
                capture_output=True, text=True, timeout=5,
            ).stdout.strip()
        except Exception:
            return "", ""
        return "", title

    return active_window, lambda: 0.0


def get_backend():
    if IS_WINDOWS:
        return _windows_backend()
    if platform.system() == "Darwin":
        return _macos_backend()
    return _linux_backend()


# --------------------------------------------------------------------------
# 추적 루프
# --------------------------------------------------------------------------
class ActivityTracker:
    def __init__(self, cfg: dict[str, Any], on_flush: Callable[[dict], None]):
        act = cfg["activity"]
        self.sample_seconds = int(act["sample_seconds"])
        self.idle_threshold = int(act["idle_threshold_seconds"])
        self.flush_seconds = int(act["flush_seconds"])
        self.ignore_titles = [t.lower() for t in act.get("ignore_titles", []) if t]
        self.on_flush = on_flush
        self.active_window, self.idle_seconds = get_backend()
        self._run: dict[str, Any] | None = None

    def _ignored(self, app: str, title: str) -> bool:
        blob = f"{app} {title}".lower()
        return any(word in blob for word in self.ignore_titles)

    def flush(self) -> None:
        run = self._run
        self._run = None
        if not run:
            return
        seconds = int(run["_end_ts"] - run["_start_ts"]) + self.sample_seconds
        self.on_flush(
            {
                "start": datetime.fromtimestamp(run["_start_ts"]).isoformat(timespec="seconds"),
                "end": datetime.fromtimestamp(run["_end_ts"]).isoformat(timespec="seconds"),
                "seconds": seconds,
                "app": run["app"],
                "title": run["title"],
            }
        )

    def sample(self) -> None:
        """한 번 관측한다. 루프에서 sample_seconds 간격으로 호출된다."""
        now = time.time()

        if self.idle_seconds() >= self.idle_threshold:
            self.flush()          # 자리비움 — 진행 중이던 세션을 끊는다
            return

        app, title = self.active_window()
        if not title and not app:
            return
        if self._ignored(app, title):
            self.flush()
            return

        run = self._run
        if run and run["app"] == app and run["title"] == title:
            run["_end_ts"] = now
            if now - run["_start_ts"] >= self.flush_seconds:
                # 장시간 같은 창 — 중간 저장해서 갑자기 꺼져도 잃지 않게 한다
                self.flush()
                self._run = {"app": app, "title": title, "_start_ts": now, "_end_ts": now}
            return

        self.flush()
        self._run = {"app": app, "title": title, "_start_ts": now, "_end_ts": now}

    def run_forever(self) -> None:
        try:
            while True:
                try:
                    self.sample()
                except Exception as exc:  # 한 번의 관측 실패로 죽지 않게
                    print(f"[track] 관측 실패: {exc}", file=sys.stderr)
                time.sleep(self.sample_seconds)
        except KeyboardInterrupt:
            pass
        finally:
            self.flush()
