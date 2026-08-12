"""LLM 없이 규칙만으로 회의록 뼈대를 뽑는다.

LLM 반입이 승인되지 않은 환경에서도 최소한 결정사항·액션아이템 후보를
추려주는 것이 목적이다. 품질은 LLM 백엔드보다 낮으므로 항상 사람이 다듬는다.
"""
from __future__ import annotations

import re
from collections import Counter

from ..models import Transcript
from ..text.postprocess import fmt_clock, split_sentences
from .schema import ActionItem, Minutes, Topic

# 결정을 나타내는 종결 표현
DECISION_PATTERNS = [
    r"하기로\s*(?:했|하겠|합니다|결정|정했)",
    r"결정(?:했|하겠|됐|되었|합니다)",
    r"확정(?:했|하겠|됐|되었|입니다|합니다)",
    r"승인(?:했|받|됐|되었|합니다)",
    r"합의(?:했|봤|됐|되었|합니다)",
    r"(?:그렇게|이대로)\s*(?:가|진행|가시)",
    r"채택(?:했|하겠|합니다)",
    r"반영(?:하기로|하겠습니다)",
]

# 할 일을 나타내는 표현
ACTION_PATTERNS = [
    r"(?:하|해|드리|보내|정리|공유|검토|확인|작성|준비|요청|취합|전달)(?:겠습니다|겠어요|ㄹ게요|을게요|기로)",
    r"부탁(?:드립니다|드릴게요|해요|합니다)",
    r"챙겨\s*(?:주세요|주시죠|보겠습니다)",
    r"(?:해|처리해|정리해|확인해|공유해)\s*주(?:세요|시겠|시길)",
    r"까지\s*(?:주세요|드리겠습니다|하겠습니다|완료)",
]

# 미결 표현
OPEN_PATTERNS = [
    r"(?:다시|추후|나중에|다음에)\s*(?:논의|보|확인|얘기|검토)",
    r"보류",
    r"확인(?:이)?\s*필요",
    r"미정",
    r"결론(?:이)?\s*안?\s*(?:났|나지)",
]

# 기한 표현
DUE_PATTERNS = [
    r"\d{1,2}\s*월\s*\d{1,2}\s*일(?:\s*까지)?",
    r"\d{1,2}/\d{1,2}(?:\s*까지)?",
    r"(?:이번|다음|차)\s*(?:주|달|분기)(?:\s*까지)?",
    r"(?:월|화|수|목|금|토|일)요일(?:\s*까지)?",
    r"(?:오늘|내일|모레|금주|내주|월말|월초|연말|반기)(?:\s*까지)?",
    r"\d+\s*일\s*(?:내|이내|안에)",
]

# 담당자 후보: 직함이 붙은 이름
OWNER_PATTERN = re.compile(
    r"([가-힣]{2,4})\s*(님|씨|책임|선임|수석|팀장|파트장|그룹장|실장|상무|전무|부장|과장|대리|사원|매니저|PM|PL)"
)

_DECISION_RE = re.compile("|".join(DECISION_PATTERNS))
_ACTION_RE = re.compile("|".join(ACTION_PATTERNS))
_OPEN_RE = re.compile("|".join(OPEN_PATTERNS))
_DUE_RE = re.compile("|".join(DUE_PATTERNS))

# 안건 후보에서 걸러낼 일반어
STOPWORDS = {
    "그것", "이것", "저것", "우리", "지금", "다음", "부분", "경우", "정도", "생각",
    "말씀", "얘기", "이야기", "내용", "부탁", "하나", "여기", "거기", "때문", "관련",
    "회의", "오늘", "감사", "네네", "예예",
}

_NOUN_CHUNK = re.compile(r"[가-힣A-Za-z][가-힣A-Za-z0-9]{1,}")


def _find_due(text: str) -> str:
    m = _DUE_RE.search(text)
    return m.group(0).strip() if m else "미정"


def _find_owner(text: str, speaker: str | None) -> str:
    m = OWNER_PATTERN.search(text)
    if m:
        return f"{m.group(1)} {m.group(2)}".strip()
    return speaker or "미정"


def _trim(sentence: str, limit: int = 120) -> str:
    sentence = sentence.strip(" -·")
    return sentence if len(sentence) <= limit else sentence[: limit - 1] + "…"


def extract_keywords(tr: Transcript, top_n: int = 6) -> list[tuple[str, float]]:
    """빈도 기반 키워드. 첫 등장 시각도 함께 돌려준다."""
    counter: Counter[str] = Counter()
    first_seen: dict[str, float] = {}
    for seg in tr.segments:
        for token in _NOUN_CHUNK.findall(seg.text):
            if len(token) < 2 or token in STOPWORDS:
                continue
            counter[token] += 1
            first_seen.setdefault(token, seg.start)
    ranked = [w for w, c in counter.most_common(top_n * 4) if c >= 2]
    return [(w, first_seen.get(w, 0.0)) for w in ranked[:top_n]]


def build(tr: Transcript, title: str = "회의록", date: str = "") -> Minutes:
    decisions: list[str] = []
    actions: list[ActionItem] = []
    open_issues: list[str] = []
    seen: set[str] = set()

    for seg in tr.segments:
        for sent in split_sentences(seg.text):
            if len(sent) < 6:
                continue
            key = sent[:40]
            if _DECISION_RE.search(sent) and key not in seen:
                seen.add(key)
                decisions.append(f"{_trim(sent)} `{fmt_clock(seg.start)}`")
            elif _ACTION_RE.search(sent) and key not in seen:
                seen.add(key)
                actions.append(ActionItem(
                    task=_trim(sent),
                    owner=_find_owner(sent, seg.speaker),
                    due=_find_due(sent),
                    source_time=seg.start,
                ))
            elif _OPEN_RE.search(sent) and key not in seen:
                seen.add(key)
                open_issues.append(f"{_trim(sent)} `{fmt_clock(seg.start)}`")

    # 키워드를 안건 제목으로 삼고, 그 단어가 처음 등장한 구간의 발화를 근거로 붙인다.
    topics: list[Topic] = []
    for word, start in extract_keywords(tr):
        points = [
            _trim(s.text)
            for s in tr.segments
            if word in s.text and len(s.text) > 15
        ][:3]
        if points:
            topics.append(Topic(title=word, points=points, start=start))

    attendees = tr.speakers
    total_chars = sum(len(s.text) for s in tr.segments)
    summary = (
        f"총 {fmt_clock(tr.duration)} 분량, 발화 {len(tr.segments)}건 "
        f"({total_chars:,}자). 결정 {len(decisions)}건 / 액션 {len(actions)}건 추출."
    )

    return Minutes(
        title=title,
        date=date,
        duration=tr.duration,
        attendees=attendees,
        summary=summary,
        topics=topics,
        decisions=decisions,
        actions=actions,
        open_issues=open_issues,
        backend="rules",
        warnings=[
            "규칙 기반 초안입니다. 문장 패턴만 보고 뽑은 것이라 "
            "누락·오탐이 있습니다. LLM 백엔드를 붙이면 품질이 크게 올라갑니다."
        ],
    )
