"""오프라인 검증. pytest 없이 그냥 실행한다.

    python weekly_report/tests/test_offline.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from weekly_report import aggregate, evidence, period  # noqa: E402
from weekly_report.config import load_config  # noqa: E402
from weekly_report.redact import Redactor  # noqa: E402
from weekly_report.summarizer import rule_based  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CHECKS: list[str] = []


def check(condition: bool, message: str) -> None:
    CHECKS.append(("OK  " if condition else "FAIL") + "  " + message)
    if not condition:
        raise AssertionError(message)


# --------------------------------------------------------------------------
def test_redact() -> None:
    redactor = Redactor({"enabled": True, "drop_keywords": ["대외비"]})

    check("[주민번호]" in redactor.text("주민 900101-1234567 확인"), "주민번호 마스킹")
    check("[카드번호]" in redactor.text("카드 1234-5678-9012-3456"), "카드번호 마스킹")
    check("[휴대전화]" in redactor.text("연락처 010-1234-5678"), "휴대전화 마스킹")
    check("[이메일]" in redactor.text("hong@example.com 로 회신"), "이메일 마스킹")
    check("[비밀키]" in redactor.text("key=sk-ant-abcdefghijklmno123"), "비밀키 마스킹")
    check(redactor.text("일반 문서 검토") == "일반 문서 검토", "일반 문장은 그대로")

    check(redactor.record({"title": "대외비 인수합병 검토"}) is None, "대외비 기록 제외")
    check(redactor.record({"title": "로드맵 검토"}) is not None, "일반 기록 유지")


def test_title_parsing() -> None:
    parsed = aggregate.parse_title("POWERPNT", "AXDX_로드맵_v3.pptx - PowerPoint")
    check(parsed["filename"] == "AXDX_로드맵_v3.pptx", "pptx 파일명 추출")
    check(parsed["kind"] == "문서", "PowerPoint → 문서")

    parsed = aggregate.parse_title("Code", "ontology_axdx.py - similar-research-DB - Visual Studio Code")
    check(parsed["filename"] == "ontology_axdx.py", "py 파일명 추출")
    check(parsed["kind"] == "개발", "VS Code → 개발")

    parsed = aggregate.parse_title("chrome", "결재함 - 사내포털")
    check(parsed["label"] == "결재함", "웹은 탭 제목 앞부분")


def test_aggregate() -> None:
    cfg = load_config(FIXTURES / "test_config.json")
    data = json.loads((FIXTURES / "sample_week.json").read_text(encoding="utf-8"))
    start, end = date(2026, 8, 10), date(2026, 8, 16)
    result = aggregate.build(cfg, start, end, data)

    names = [p["name"] for p in result["projects"]]
    check("AX/DX 추진 로드맵" in names, "과제 분류 동작")

    roadmap = next(p for p in result["projects"] if p["name"] == "AX/DX 추진 로드맵")
    pptx = next(i for i in roadmap["items"] if i["label"] == "AXDX_로드맵_v3.pptx")

    # 월(1.6h) + 화(1.5h) + 목(2.5h) 세션이 하나로 합쳐져야 한다
    check(pptx["seconds"] == 5760 + 5400 + 9000, "같은 문서의 세션 합산")
    check(pptx["days"] == ["월", "화", "목"], "요일이 순서대로 모임")

    # 목요일 11:20 파일 수정이 목요일 세션(09:00~11:30) 안에 있으므로 작성으로 승격
    check(pptx["status"] == "작성·수정", "파일 수정시각 교차검증 → 작성·수정")

    portal_project, portal = next(
        (p["name"], i)
        for p in result["projects"] for i in p["items"] if i["label"] == "결재함"
    )
    check(portal["status"] == "검토·열람", "파일 수정 근거가 없으면 검토·열람")
    # 'rom' 이 프로세스명 'chrome' 에 부분 일치해 ROM 과제로 새면 안 된다.
    # '결재' 키워드가 있으므로 부서 운영이 정답이다.
    check(portal_project == "부서 운영", "영문 키워드는 단어 경계를 지킴")

    classifier = aggregate.ProjectClassifier(cfg["projects"])
    check(classifier.classify("chrome", "결재함") != "설계 시뮬레이션 ROM",
          "'chrome' 이 'rom' 에 걸리지 않음")
    check(classifier.classify("ROM 검증 계획") == "설계 시뮬레이션 ROM",
          "진짜 'ROM' 은 여전히 매칭")

    # 30초짜리 탐색기 세션은 min_session_seconds 로 걸러진다
    labels = [i["label"] for p in result["projects"] for i in p["items"]]
    check("다운로드" not in labels, "짧은 세션 제거")

    check(result["totals"]["meetings"] == 2, "회의 2건 집계")
    check(result["totals"]["sent_mails"] == 2, "보낸 메일 2건 집계")
    check(result["totals"]["commits"] == 2, "커밋 2건 집계")
    check(all(result["coverage"].values()), "네 소스 모두 수집됨으로 표시")
    return cfg, result


def test_report_render(cfg, result) -> str:
    pack = evidence.build_pack(result, Redactor(cfg["redact"]))
    payload = evidence.to_prompt_payload(pack)

    check("기간" in payload and "과제별_활동" in payload, "LLM 입력 구조 생성")
    blob = json.dumps(payload, ensure_ascii=False)
    check("@example.com" not in blob, "외부로 나갈 내용에 이메일 주소 없음")

    text = rule_based.render(pack)
    check(text.startswith("# 주간업무보고"), "마크다운 제목")
    check("## 1. 금주 실적" in text, "실적 섹션")
    check("## 2. 회의·협의" in text, "회의 섹션")
    check("AXDX_로드맵_v3.pptx" in text, "문서명이 실적에 나옴")
    check("ROM 개발 진도 점검 회의" in text, "회의가 회의 섹션에 나옴")
    return text


def test_llm_adapter() -> None:
    """네트워크 없이 요청 조립과 응답 파싱만 확인한다."""
    from weekly_report.summarizer import inhouse_llm

    url, headers, body = inhouse_llm.build_request(
        {"api_style": "openai", "base_url": "http://llm.local/v1", "model": "in-house-7b"},
        "테스트 프롬프트",
    )
    check(url == "http://llm.local/v1/chat/completions", "OpenAI 호환 URL 조립")
    check(body["messages"][1]["content"] == "테스트 프롬프트", "프롬프트가 본문에 들어감")
    check("Authorization" not in headers, "키가 없으면 인증 헤더 없음")

    import os

    os.environ["WR_TEST_KEY"] = "secret-token"
    _, headers, _ = inhouse_llm.build_request(
        {"api_style": "openai", "base_url": "http://llm.local/v1",
         "model": "m", "api_key_env": "WR_TEST_KEY"},
        "x",
    )
    check(headers["Authorization"] == "Bearer secret-token", "환경변수에서 키를 읽음")

    url, _, body = inhouse_llm.build_request(
        {
            "api_style": "custom",
            "base_url": "http://llm.local/api/generate",
            "request_template": {"prompt": "{{SYSTEM}}\n{{PROMPT}}", "max_new_tokens": 512},
        },
        "테스트 프롬프트",
    )
    check(url == "http://llm.local/api/generate", "custom 은 base_url 을 그대로 사용")
    check(body["prompt"].endswith("테스트 프롬프트"), "custom 템플릿 치환")
    check(body["max_new_tokens"] == 512, "custom 템플릿의 다른 필드 유지")

    sample = {"result": {"text": "정상"}}
    check(inhouse_llm._dig(sample, "result.text") == "정상", "응답 경로 탐색")
    check(inhouse_llm._dig({"choices": [{"message": {"content": "안녕"}}]},
                           "choices.0.message.content") == "안녕", "배열 인덱스 경로")


def test_period() -> None:
    start, end = period.resolve("2026-W33")
    check((start, end) == (date(2026, 8, 10), date(2026, 8, 16)), "ISO 주차 해석")
    start, end = period.resolve("2026-08-12")
    check((start, end) == (date(2026, 8, 10), date(2026, 8, 16)), "날짜 → 그 주")
    check(period.hm(9000) == "2시간 30분", "시간 표기")


def main() -> int:
    test_redact()
    test_title_parsing()
    test_period()
    test_llm_adapter()
    cfg, result = test_aggregate()
    text = test_report_render(cfg, result)

    print("\n".join(CHECKS))
    print(f"\n{len(CHECKS)}개 확인 통과\n")
    print("=" * 60)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
