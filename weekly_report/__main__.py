"""weekly_report CLI.

    python -m weekly_report track                # 상시 실행 (활성 창 기록)
    python -m weekly_report collect --week this  # 메일·문서·커밋 수집
    python -m weekly_report report --week this   # 주간보고 초안 생성
    python -m weekly_report run --week this      # collect + report
    python -m weekly_report llm-check            # 사내 LLM 연결 확인
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

from . import aggregate, evidence, period, summarizer
from .config import data_dir, load_config, report_dir
from .redact import Redactor
from .storage import Store

TEMPLATE_DEFAULT = Path(__file__).resolve().parent / "templates" / "weekly_ko.md"


# --------------------------------------------------------------------------
def cmd_track(args, cfg: dict) -> int:
    from .collectors.activity import ActivityTracker

    store = Store(data_dir(cfg))
    redactor = Redactor(cfg["redact"])

    def on_flush(record: dict) -> None:
        cleaned = redactor.record(record)
        if cleaned:
            store.append("activity", cleaned)

    tracker = ActivityTracker(cfg, on_flush)
    print(f"[track] 기록 시작 — {data_dir(cfg) / 'activity'}")
    print(f"[track] {tracker.sample_seconds}초 간격, "
          f"{tracker.idle_threshold}초 무입력 시 중단. 종료는 Ctrl+C.")
    tracker.run_forever()
    print("\n[track] 종료했습니다.")
    return 0


# --------------------------------------------------------------------------
def cmd_collect(args, cfg: dict) -> int:
    from .collectors import files as files_collector
    from .collectors import gitlog

    start, end = period.resolve(args.week)
    store = Store(data_dir(cfg))
    redactor = Redactor(cfg["redact"])
    print(f"[collect] 대상 기간: {period.label(start, end)}")

    # 메일·일정
    if cfg["outlook"].get("enabled", True):
        try:
            from .collectors import outlook

            records = redactor.records(list(outlook.collect(cfg, start, end)))
            count = store.replace_range("mail", start, end, records)
            mails = sum(1 for r in records if r.get("kind") == "mail")
            print(f"[collect] Outlook: 메일 {mails}건, 회의 {count - mails}건")
        except Exception as exc:
            print(f"[collect] Outlook 수집 실패 (건너뜁니다): {exc}", file=sys.stderr)
            print("          → 사내 정책으로 막힌 경우 'import-mail' 로 CSV 를 넣을 수 있습니다.",
                  file=sys.stderr)

    # 수정 문서
    if cfg["files"].get("enabled", True):
        records = redactor.records(list(files_collector.collect(cfg, start, end)))
        store.replace_range("files", start, end, records)
        print(f"[collect] 수정 문서: {len(records)}건")

    # git 커밋
    if cfg["git"].get("enabled", True):
        records = redactor.records(list(gitlog.collect(cfg, start, end)))
        store.replace_range("git", start, end, records)
        print(f"[collect] git 커밋: {len(records)}건")

    activity = store.read_range("activity", start, end)
    print(f"[collect] 기존 화면 기록: {len(activity)}건")
    if not activity:
        print("          → 'track' 을 상시 실행해두면 소요시간까지 채워집니다.")
    return 0


# --------------------------------------------------------------------------
def load_template(cfg: dict) -> str:
    custom = cfg["report"].get("template", "")
    path = Path(custom).expanduser() if custom else TEMPLATE_DEFAULT
    if not path.exists():
        path = TEMPLATE_DEFAULT
    return path.read_text(encoding="utf-8")


def load_data(cfg: dict, start: date, end: date, fixture: str | None) -> dict[str, list]:
    if fixture:
        raw = json.loads(Path(fixture).expanduser().read_text(encoding="utf-8"))
        return {key: raw.get(key, []) for key in ("activity", "mail", "files", "git")}
    store = Store(data_dir(cfg))
    return {key: store.read_range(key, start, end)
            for key in ("activity", "mail", "files", "git")}


def cmd_report(args, cfg: dict) -> int:
    start, end = period.resolve(args.week)
    data = load_data(cfg, start, end, args.fixture)

    total = sum(len(v) for v in data.values())
    if total == 0:
        print("[report] 이 기간에 수집된 기록이 없습니다. 먼저 collect 를 실행하세요.",
              file=sys.stderr)
        return 1

    result = aggregate.build(cfg, start, end, data)
    pack = evidence.build_pack(result, Redactor(cfg["redact"]))

    out = report_dir(cfg)
    slug = pack["period"]["slug"]
    evidence_path = evidence.save(pack, out / f"evidence_{slug}.json")
    print(f"[report] 근거 묶음: {evidence_path}")

    payload = evidence.to_prompt_payload(pack)
    if args.dry_run:
        payload_path = out / f"payload_{slug}.json"
        payload_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"[report] LLM 으로 나갈 내용(미발송): {payload_path}")

    if args.dry_run and cfg["llm"].get("enabled"):
        from .summarizer import rule_based

        text, source = rule_based.render(pack), "규칙 기반 (dry-run)"
    else:
        text, source = summarizer.summarize(cfg, pack, payload, load_template(cfg))

    report_path = out / f"weekly_{slug}.md"
    report_path.write_text(text, encoding="utf-8")

    print(f"[report] 생성 방식: {source}")
    print(f"[report] 초안: {report_path}")
    _print_summary(pack)
    return 0


def _print_summary(pack: dict) -> None:
    totals = pack.get("totals", {})
    print(
        f"\n  PC 활동 {totals.get('tracked_hours', 0)}h · "
        f"회의 {totals.get('meeting_hours', 0)}h · "
        f"문서 {totals.get('files', 0)}건 · "
        f"메일 {totals.get('sent_mails', 0)}건 · "
        f"커밋 {totals.get('commits', 0)}건"
    )
    for project in pack.get("projects", [])[:6]:
        print(f"    - {project['name']}: {period.hm(project['seconds'])}")
    missing = [name for name, ok in pack.get("coverage", {}).items() if not ok]
    if missing:
        print(f"  ※ 수집되지 않은 소스: {', '.join(missing)}")


# --------------------------------------------------------------------------
def cmd_run(args, cfg: dict) -> int:
    code = cmd_collect(args, cfg)
    if code != 0:
        return code
    print()
    return cmd_report(args, cfg)


def cmd_llm_check(args, cfg: dict) -> int:
    from .summarizer import inhouse_llm

    llm_cfg = cfg["llm"]
    if not llm_cfg.get("base_url"):
        print("[llm-check] llm.base_url 이 비어 있습니다. config 를 먼저 채워주세요.",
              file=sys.stderr)
        return 1
    print(f"[llm-check] 대상: {llm_cfg.get('base_url')} / 모델: {llm_cfg.get('model')}")
    try:
        answer = inhouse_llm.check(llm_cfg)
    except Exception as exc:
        print(f"[llm-check] 실패: {exc}", file=sys.stderr)
        print("           응답 형식이 다르면 llm.response_path 를 조정하세요.", file=sys.stderr)
        return 1
    print(f"[llm-check] 응답: {answer.strip()[:200]}")
    print("[llm-check] 정상입니다. config 의 llm.enabled 를 true 로 바꾸세요.")
    return 0


def cmd_import_mail(args, cfg: dict) -> int:
    from .collectors.outlook import import_mail_csv

    start, end = period.resolve(args.week)
    store = Store(data_dir(cfg))
    redactor = Redactor(cfg["redact"])
    records = redactor.records(list(import_mail_csv(args.path)))
    kept = []
    for record in records:
        when = period.parse_ts(record.get("time", ""))
        if when and start <= when.date() <= end:
            record["time"] = when.isoformat(timespec="seconds")
            kept.append(record)
    store.extend("mail", kept)
    print(f"[import-mail] {len(kept)}건을 {period.label(start, end)} 로 추가했습니다.")
    return 0


# --------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m weekly_report",
        description="한 주 동안의 활동 기록으로 주간보고 초안을 만듭니다.",
    )
    parser.add_argument("--config", help="설정 파일 경로")
    sub = parser.add_subparsers(dest="command", required=True)

    # --config 를 서브커맨드 뒤에 써도 동작하게 한다.
    # SUPPRESS 라서 지정하지 않으면 앞쪽 값이 그대로 유지된다.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", default=argparse.SUPPRESS, help="설정 파일 경로")

    def add_week(target):
        target.add_argument(
            "--week", default="this",
            help="this | last | 2026-W33 | 2026-08-12 (기본값: this)",
        )

    sub.add_parser("track", help="활성 창 기록 (상시 실행)",
                   parents=[common]).set_defaults(func=cmd_track)

    collect = sub.add_parser("collect", help="메일·문서·커밋 수집", parents=[common])
    add_week(collect)
    collect.set_defaults(func=cmd_collect)

    report = sub.add_parser("report", help="주간보고 초안 생성", parents=[common])
    add_week(report)
    report.add_argument("--dry-run", action="store_true",
                        help="LLM 을 호출하지 않고, 나갈 내용만 파일로 저장")
    report.add_argument("--fixture", help="테스트용 수집 데이터 JSON")
    report.set_defaults(func=cmd_report)

    run = sub.add_parser("run", help="collect + report", parents=[common])
    add_week(run)
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--fixture", help=argparse.SUPPRESS)
    run.set_defaults(func=cmd_run)

    sub.add_parser("llm-check", help="사내 LLM 연결 확인",
                   parents=[common]).set_defaults(func=cmd_llm_check)

    imp = sub.add_parser("import-mail", help="Outlook 에서 내보낸 CSV 넣기", parents=[common])
    imp.add_argument("path", help="CSV 파일 경로")
    add_week(imp)
    imp.set_defaults(func=cmd_import_mail)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not hasattr(args, "fixture"):
        args.fixture = None
    cfg = load_config(args.config)
    try:
        return args.func(args, cfg)
    except ValueError as exc:
        print(f"[!] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
