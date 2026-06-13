"""
사무실 작업지시 큐 실행 — queued → in_progress → done.

담당 에이전트 연구 → 사서 젬마 취합 → 완료 보고.

  python scripts/agent_office_task_runner.py process
  python scripts/agent_office_task_runner.py process --max 3
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

BOARD = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("BOARD_DB_PATH", str(BOARD / "board.db")))

if str(BOARD / "scripts") not in sys.path:
    sys.path.insert(0, str(BOARD / "scripts"))

import agent_office_tasks
import agent_office_log
import agent_office_research
import agent_registry


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def resolve_agent_id(task: dict) -> str:
    resolved = (task.get("resolved_to") or "").strip()
    division = (task.get("division") or "finance").strip()
    if resolved and resolved != "all":
        return resolved
    return agent_office_research.pick_agent_for_instruction(
        task.get("body") or "",
        task.get("assign_to") or "all",
        division=division,
    )


def requeue_stale_tasks(*, minutes: int = 30) -> int:
    """오래된 in_progress 작업을 queued로 복구."""
    from datetime import timedelta

    cutoff = datetime.now() - timedelta(minutes=max(5, minutes))
    n = 0
    for t in agent_office_tasks.load_tasks().get("tasks") or []:
        if not isinstance(t, dict) or t.get("status") != "in_progress":
            continue
        started = (t.get("started_at") or "").strip()
        if not started:
            continue
        try:
            ts = datetime.strptime(started, "%Y-%m-%d %H:%M")
        except ValueError:
            continue
        if ts <= cutoff:
            agent_office_tasks.update_task(
                t["id"],
                status="queued",
                last_error="처리 시간 초과 — 재시도",
                finished_at="",
            )
            n += 1
    return n


def synthesizer_for(task: dict, primary_id: str) -> str:
    division = (task.get("division") or "finance").strip()
    return agent_office_research.synthesizer_agent(primary_id, division=division)


def agent_is_available(agent_id: str, registry: dict) -> bool:
    if agent_registry.is_office_active(registry):
        return True
    for a in registry.get("agents") or []:
        if isinstance(a, dict) and a.get("id") == agent_id:
            return bool(a.get("mode_on"))
    if agent_id.startswith("saju_"):
        return agent_id == "saju_reader"
    if agent_id.startswith("kiwoom_"):
        return agent_id == "kiwoom_reader"
    return agent_id == "researcher"


def _is_council_task(task: dict) -> bool:
    try:
        import agent_office_council

        return (task.get("source") or "") in (
            agent_office_council.SOURCE_COUNCIL_SAJU,
            agent_office_council.SOURCE_COUNCIL_FINANCE,
        )
    except Exception:
        return False


def _is_card_council_task(task: dict) -> bool:
    try:
        import agent_office_saju_card_council

        return (task.get("source") or "") == agent_office_saju_card_council.SOURCE_COUNCIL_SAJU_CARD
    except Exception:
        return False


def process_one_task(task: dict, registry: dict, *, chain_next: bool = False) -> bool:
    tid = task.get("id")
    if not isinstance(tid, int):
        return False

    if _is_card_council_task(task):
        try:
            import agent_office_saju_card_council

            ok, _summary = agent_office_saju_card_council.process_card_council_task(
                task, registry
            )
            agent_registry.update_agent_run("saju_structurer", f"card_council#{tid}")
            try:
                import agent_office_saju_reserved_tasks

                agent_office_saju_reserved_tasks.ensure_reserved_queue()
            except Exception:
                pass
            return ok
        except Exception as e:
            agent_office_tasks.update_task(
                tid,
                status="done",
                finished_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
                result=f"카드 위원회 오류: {e!s}"[:500],
            )
            return False

    if _is_council_task(task):
        try:
            import agent_office_council

            ok, _summary = agent_office_council.process_council_task(task, registry)
            division = (task.get("division") or "finance").strip()
            primary_id = (
                "saju_structurer" if division == "saju-learn" else "structurer"
            )
            agent_registry.update_agent_run(primary_id, f"council#{tid}")
            try:
                import agent_office_reserved_tasks
                import agent_office_kiwoom_reserved_tasks
                import agent_office_saju_reserved_tasks
                import agent_office_chief_dev_reserved_tasks

                agent_office_reserved_tasks.ensure_reserved_queue()
                agent_office_saju_reserved_tasks.ensure_reserved_queue()
                agent_office_kiwoom_reserved_tasks.ensure_reserved_queue()
                agent_office_chief_dev_reserved_tasks.ensure_reserved_queue()
            except Exception:
                pass
            return ok
        except Exception as e:
            agent_office_tasks.update_task(
                tid,
                status="queued",
                last_error=str(e)[:200],
            )
            agent_office_log.append_message(
                from_id="ceo",
                kind="system",
                text=f"[위원회 #{tid} 오류] {e!s}"[:500],
            )
            return False

    primary_id = resolve_agent_id(task)
    synth_id = synthesizer_for(task, primary_id)

    if not agent_is_available(primary_id, registry):
        agent_office_tasks.update_task(
            tid,
            status="queued",
            last_error=f"{primary_id} OFF — 다음 주기에 재시도",
        )
        return False

    assign_label = agent_office_research.agent_display(primary_id, registry)
    agent_office_tasks.update_task(
        tid,
        status="in_progress",
        started_at=_now(),
        handled_by=primary_id,
        resolved_to=primary_id,
    )

    body_preview = (task.get("body") or "")[:200]
    agent_office_log.append_message(
        from_id="ceo",
        to_id=primary_id,
        kind="task",
        text=f"[작업 #{tid} 전달] {assign_label}에게 지시했습니다.\n{body_preview}",
    )
    agent_office_log.append_message(
        from_id=primary_id,
        to_id=synth_id,
        kind="handoff",
        text=f"[작업 #{tid} 연구 시작] 지시 내용을 조사합니다.",
    )

    try:
        notes = agent_office_research.gather_research(task, primary_id)
        research_lines = [
            f"  · [{n.source}] {n.title}" for n in notes if n.source != "instruction"
        ][:8]
        agent_office_log.append_message(
            from_id=primary_id,
            to_id="ceo",
            kind="task",
            text=f"[작업 #{tid} 연구 수집]\n" + ("\n".join(research_lines) or "  · 수집 항목 없음"),
        )

        agent_office_log.append_message(
            from_id=primary_id,
            to_id=synth_id,
            kind="handoff",
            text=f"[작업 #{tid}] 연구 자료 {max(0, len(notes) - 1)}건을 사서에게 전달 — 취합 요청",
        )

        result = agent_office_research.synthesize_report(
            task, primary_id, synth_id, notes, registry
        )

        agent_office_tasks.update_task(
            tid,
            status="done",
            finished_at=_now(),
            handled_by=primary_id,
            resolved_to=primary_id,
            synthesized_by=synth_id,
            result=result[:4000],
        )

        division = (task.get("division") or "finance").strip()
        wiki_id = None
        wiki_card = None
        if division not in ("saju-learn", "kiwoom-chasu"):
            try:
                import agent_office_wiki_store

                wiki_card = agent_office_wiki_store.save_task_to_knowledge(
                    {**task, "finished_at": _now(), "result": result[:4000]},
                    result,
                    primary_id=primary_id,
                    synth_id=synth_id,
                )
                if wiki_card:
                    wiki_id = wiki_card.get("id")
            except Exception as e:
                agent_office_log.append_message(
                    from_id="structurer",
                    kind="system",
                    text=f"[10_Wiki 저장 실패 #{tid}] {e!s}"[:300],
                )
            agent_office_tasks.update_task(tid, wiki_id=wiki_id)

        blog_draft_id = None
        if division not in ("saju-learn", "kiwoom-chasu"):
            try:
                import agent_office_blog_draft

                blog_draft_id = agent_office_blog_draft.create_draft_from_task(
                    {**task, "finished_at": _now(), "result": result[:4000]},
                    result,
                    primary_id=primary_id,
                )
                if blog_draft_id:
                    agent_office_tasks.update_task(tid, blog_draft_id=blog_draft_id)
            except Exception as e:
                agent_office_log.append_message(
                    from_id="creator",
                    kind="system",
                    text=f"[블로그 초안 실패 #{tid}] {e!s}"[:300],
                )

        conclusion = f"[작업 #{tid} 완료 — {assign_label} 연구 + 취합]\n{result[:1500]}"
        if wiki_id:
            conclusion += f"\n\n📗 10_Wiki 저장: {wiki_id}"
        if blog_draft_id:
            conclusion += f"\n\n📝 블로그 초안: post #{blog_draft_id} (미공개)"
        agent_office_log.append_message(
            from_id=synth_id,
            to_id="ceo",
            kind="conclusion",
            text=conclusion,
        )
        if wiki_id:
            agent_office_log.append_message(
                from_id="structurer",
                to_id="ceo",
                kind="system",
                text=f"[10_Wiki] {wiki_card.get('title', wiki_id)} — 메타 {len(wiki_card.get('tags') or [])}개 태그 색인",
            )
        if blog_draft_id:
            agent_office_log.append_message(
                from_id="creator",
                to_id="ceo",
                kind="system",
                text=(
                    f"[블로그 초안 #{blog_draft_id}] 작업 #{tid} — "
                    f"미리보기 /post/{blog_draft_id} · 수정 /post/{blog_draft_id}/edit "
                    f"(사무실에서 발행 가능)"
                ),
            )

        try:
            if division in ("saju-learn", "kiwoom-chasu"):
                raise RuntimeError("skip_cursor")
            import agent_office_cursor_bridge

            agent_office_cursor_bridge.push_completion(
                {**task, "finished_at": _now(), "result": result[:4000]},
                result=result,
                wiki_id=wiki_id,
                blog_draft_id=blog_draft_id,
            )
            agent_office_log.append_message(
                from_id="structurer",
                to_id="ceo",
                kind="system",
                text=(
                    f"[Cursor 연동] 작업 #{tid} — CURSOR_OFFICE_INBOX.md 에 반영됨. "
                    f"Cursor에서 `sync_cursor_office_inbox.py pull` 후 처리"
                )[:400],
            )
        except Exception:
            pass

        agent_registry.update_agent_run(primary_id, f"task#{tid}")
        agent_registry.update_agent_run(synth_id, f"sync#{tid}")

        try:
            import agent_office_reserved_tasks
            import agent_office_kiwoom_reserved_tasks
            import agent_office_chief_dev_reserved_tasks

            agent_office_reserved_tasks.ensure_reserved_queue()
            agent_office_saju_reserved_tasks.ensure_reserved_queue()
            agent_office_kiwoom_reserved_tasks.ensure_reserved_queue()
            agent_office_chief_dev_reserved_tasks.ensure_reserved_queue()
        except Exception:
            pass

        if chain_next:
            nxt = agent_office_tasks.list_queued_tasks()
            nxt.sort(
                key=lambda t: (
                    0 if t.get("priority") == "high" else 1,
                    t.get("id") or 0,
                )
            )
            if nxt:
                process_one_task(nxt[0], registry, chain_next=False)
        return True
    except Exception as e:
        agent_office_tasks.update_task(
            tid,
            status="queued",
            last_error=str(e)[:200],
        )
        agent_office_log.append_message(
            from_id=primary_id,
            kind="system",
            text=f"[작업 #{tid} 오류] {e!s}"[:500],
        )
        return False


def _pick_fair_batch(queued: list[dict], *, limit: int) -> list[dict]:
    """명리·금융 대기를 한 사이클에 골고루 처리 (금융만 소진되는 것 방지)."""
    if limit <= 0 or not queued:
        return []

    def _sort_key(t: dict) -> tuple:
        return (
            0 if t.get("priority") == "high" else 1,
            t.get("id") or 0,
        )

    finance = sorted(
        [
            t
            for t in queued
            if (t.get("division") or "finance").strip()
            not in ("saju-learn", "kiwoom-chasu")
        ],
        key=_sort_key,
    )
    saju = sorted(
        [t for t in queued if (t.get("division") or "").strip() == "saju-learn"],
        key=_sort_key,
    )
    kiwoom = sorted(
        [t for t in queued if (t.get("division") or "").strip() == "kiwoom-chasu"],
        key=_sort_key,
    )
    chief_dev = sorted(
        [t for t in queued if (t.get("division") or "").strip() == "chief-dev"],
        key=_sort_key,
    )
    buckets = [b for b in (saju, kiwoom, chief_dev, finance) if b]
    if len(buckets) == 1:
        return buckets[0][:limit]
    per = max(1, limit // len(buckets))
    batch: list[dict] = []
    for b in buckets:
        batch.extend(b[:per])
    return batch[:limit]


def process_queued_tasks(*, max_tasks: int = 4) -> int:
    try:
        import agent_office_kiwoom_reserved_tasks
        import agent_office_reserved_tasks
        import agent_office_saju_reserved_tasks
        import agent_office_chief_dev_reserved_tasks

        agent_office_reserved_tasks.ensure_reserved_queue()
        agent_office_saju_reserved_tasks.ensure_reserved_queue()
        agent_office_kiwoom_reserved_tasks.ensure_reserved_queue()
        agent_office_chief_dev_reserved_tasks.ensure_reserved_queue()
    except Exception as e:
        print(f"[task_runner] ensure reserved queues failed: {e}", flush=True)

    requeue_stale_tasks()

    registry = agent_registry.load_registry()
    queued = agent_office_tasks.list_queued_tasks()
    batch = _pick_fair_batch(queued, limit=max(1, max_tasks))

    done = 0
    for task in batch:
        if process_one_task(task, registry, chain_next=False):
            done += 1

    if done:
        feed = agent_office_log.load_feed()
        feed["updated_at"] = _now()
        agent_office_log.save_feed(feed)

    return done


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("process")
    pr.add_argument("--max", type=int, default=5)

    args = p.parse_args()
    if args.cmd == "process":
        n = process_queued_tasks(max_tasks=max(1, args.max))
        print(f"processed={n}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
