"""전사 결과 텍스트 정리. 외부 의존 없음 — 순수 문자열 처리라 테스트가 쉽다."""
from __future__ import annotations

import re

from ..models import Segment, Transcript

# 한국어 회의 녹취에서 반복적으로 끼는 간투어.
# '그', '저' 같은 지시관형사는 뒤에 명사가 붙으면 의미가 있으므로
# 홀로 떨어진 토큰일 때만 제거한다.
FILLERS = [
    "어", "음", "아", "에", "그", "저", "뭐", "이제", "인제",
    "어어", "음음", "아아", "그니까", "그러니까요", "저기요", "뭐랄까",
    "아시다시피", "뭐지", "그쵸", "그죠",
]

_SPACES = re.compile(r"[ \t 　]+")
_SENT_END = re.compile(r"(?<=[.!?。！？])\s+|(?<=[다요](?:\.|!|\?))\s+")
_REPEAT_CHAR = re.compile(r"(.)\1{4,}")


def normalize_spaces(text: str) -> str:
    """중복 공백·문장부호 앞 공백 정리."""
    text = _SPACES.sub(" ", text.replace("\r\n", "\n"))
    text = re.sub(r"\s+([,.!?;:%)\]}])", r"\1", text)
    text = re.sub(r"([(\[{])\s+", r"\1", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def remove_fillers(text: str, fillers: list[str] | None = None) -> str:
    """홀로 떨어진 간투어만 제거한다. '그 부분은' 의 '그' 는 보존."""
    words = fillers if fillers is not None else FILLERS
    if not words:
        return text
    pattern = "|".join(sorted((re.escape(w) for w in words), key=len, reverse=True))
    # 앞뒤가 공백/문장부호/문자열 경계인 경우에만 매칭
    text = re.sub(rf"(?<![가-힣A-Za-z0-9])(?:{pattern})(?=[\s,.…]|$)", " ", text)
    text = re.sub(r"\s*,\s*,+", ",", text)
    return normalize_spaces(text)


def collapse_repeats(text: str, max_repeat: int = 2) -> str:
    """Whisper 가 무음 구간에서 같은 어구를 무한 반복하는 현상을 접는다."""
    text = _REPEAT_CHAR.sub(lambda m: m.group(1) * 3, text)
    tokens = text.split()
    out: list[str] = []
    run = 1
    for tok in tokens:
        if out and tok == out[-1]:
            run += 1
            if run > max_repeat:
                continue
        else:
            run = 1
        out.append(tok)
    text = " ".join(out)

    # 어구(2~8 단어) 단위 반복도 접는다.
    for size in range(8, 1, -1):
        pattern = re.compile(r"\b((?:\S+\s+){%d}\S+)(?:\s+\1\b)+" % (size - 1))
        text = pattern.sub(r"\1", text)
    return normalize_spaces(text)


def split_sentences(text: str) -> list[str]:
    """한국어 종결어미(-다./-요.)와 일반 문장부호 기준 분리."""
    text = normalize_spaces(text)
    if not text:
        return []
    parts = [p.strip() for p in _SENT_END.split(text) if p and p.strip()]
    return parts or [text]


def clean_segment_text(text: str, drop_fillers: bool = True) -> str:
    text = collapse_repeats(normalize_spaces(text))
    if drop_fillers:
        text = remove_fillers(text)
    return text


def clean_transcript(tr: Transcript, drop_fillers: bool = True) -> Transcript:
    segs: list[Segment] = []
    for s in tr.segments:
        cleaned = clean_segment_text(s.text, drop_fillers=drop_fillers)
        if not cleaned:
            continue
        segs.append(Segment(start=s.start, end=s.end, text=cleaned, speaker=s.speaker))
    return Transcript(
        segments=segs, language=tr.language, duration=tr.duration,
        source=tr.source, meta=dict(tr.meta),
    )


def merge_by_speaker(tr: Transcript, max_gap: float = 1.2) -> Transcript:
    """같은 화자가 연달아 말한 토막을 한 문단으로 합친다."""
    merged: list[Segment] = []
    for s in tr.segments:
        prev = merged[-1] if merged else None
        if (
            prev is not None
            and prev.speaker == s.speaker
            and s.start - prev.end <= max_gap
        ):
            prev.text = normalize_spaces(f"{prev.text} {s.text}")
            prev.end = s.end
        else:
            merged.append(Segment(s.start, s.end, s.text, s.speaker))
    return Transcript(
        segments=merged, language=tr.language, duration=tr.duration,
        source=tr.source, meta=dict(tr.meta),
    )


def chunk_for_tts(text: str, max_chars: int = 220) -> list[str]:
    """TTS 엔진에 넣을 크기로 자른다. 문장 경계를 최대한 지킨다."""
    if max_chars <= 0:
        raise ValueError("max_chars 는 1 이상이어야 합니다.")
    chunks: list[str] = []
    buf = ""
    for sent in split_sentences(text):
        while len(sent) > max_chars:
            # 한 문장이 통째로 길면 쉼표 → 공백 순으로 끊는다.
            cut = sent.rfind(",", 0, max_chars)
            if cut < max_chars // 2:
                cut = sent.rfind(" ", 0, max_chars)
            if cut <= 0:
                cut = max_chars
            head, sent = sent[: cut + 1].strip(), sent[cut + 1 :].strip()
            if buf:
                chunks.append(buf)
                buf = ""
            chunks.append(head)
        if not sent:
            continue
        if not buf:
            buf = sent
        elif len(buf) + 1 + len(sent) <= max_chars:
            buf = f"{buf} {sent}"
        else:
            chunks.append(buf)
            buf = sent
    if buf:
        chunks.append(buf)
    return chunks


def chunk_for_llm(tr: Transcript, max_chars: int = 6000) -> list[str]:
    """긴 회의를 LLM 컨텍스트에 맞게 시간 순으로 나눈다."""
    chunks: list[str] = []
    buf: list[str] = []
    size = 0
    for s in tr.segments:
        line = f"[{fmt_clock(s.start)}] {s.speaker or '화자'}: {s.text}"
        if size + len(line) > max_chars and buf:
            chunks.append("\n".join(buf))
            buf, size = [], 0
        buf.append(line)
        size += len(line) + 1
    if buf:
        chunks.append("\n".join(buf))
    return chunks


def fmt_clock(seconds: float) -> str:
    """00:12:34 형태."""
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
