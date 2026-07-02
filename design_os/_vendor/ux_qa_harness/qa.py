#!/usr/bin/env python3
"""UX-QA Harness deterministic capture pass.

Reuses the recorder driver (lib/auth, lib/spec, record._drive_entry) to walk
every route in a site spec. It captures deterministic UX-QA signals:

  - console errors + uncaught page exceptions (JS broke on the page)
  - failed network responses (HTTP >= 400) + request failures, tagged
    same-origin / api so app/API failures outrank third-party noise
  - selector misses: a spec action whose element never resolved - a broken or
    moved affordance the recorder logs as `skipped: True`
  - navigation failures: route bounced / never authenticated
  - accessibility issues from a deterministic page scan
  - optional visual baseline diffs from captured screenshots
  - a screenshot per route (input for the later vision-triage layer)

Emits into the run dir ($UXQA_RUNTIME_ROOT/runs/<ts>-qa/):
  qa-manifest.json   structured per-route findings + run metadata
  report.md          severity-bucketed digest (human + `claude -p` readable)
  digest-line.txt    one-liner for the morning digest

Phase 0 is deterministic only. The cascade vision/Claude triage and the
PostHog rage/dead-click mirror entries layer on top of this manifest later.

Usage:
  .venv/bin/python qa.py                                  # configured site
  .venv/bin/python qa.py --base-url https://<preview>.vercel.app
  .venv/bin/python qa.py --only home --headed
  .venv/bin/python qa.py --limit 3                         # smoke: first N routes
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import sys
import time
import traceback
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))

from lib import a11y, auth, env, spec, visual  # noqa: E402
import record  # reuse driver primitives - no edits to record.py  # noqa: E402


# ---- signal capture -------------------------------------------------------

# Known third-party scripts whose console noise is usually not an app bug. App-origin
# errors stay load-bearing; these get downgraded so nightly alerts don't cry wolf.
THIRD_PARTY = (
    "helpscout", "beacon", "posthog", "stripe", "googletagmanager",
    "google-analytics", "gstatic", "sentry", "hotjar", "intercom",
    "doubleclick", "facebook", "fbcdn", "clarity.ms", "cloudflareinsights",
)


def _is_third_party(text: str, url: str, host: str) -> bool:
    blob = (text + " " + (url or "")).lower()
    if any(d in blob for d in THIRD_PARTY):
        return True
    h = urlparse(url).netloc if url else ""
    return bool(h and h != host)


def _attach_listeners(page, host: str) -> dict[str, list]:
    """Wire console/pageerror/network collectors onto a page. Returns the
    mutable buffers; attach BEFORE navigation so load-time errors are caught."""
    buf: dict[str, list] = {"console_errors": [], "page_errors": [], "failed_responses": []}

    def on_console(msg):
        if msg.type != "error":
            return
        text = (msg.text or "")[:500]
        # "Failed to load resource" is redundant with the network capture below,
        # which is already origin-tagged - drop it to cut duplicate noise.
        if text.startswith("Failed to load resource"):
            return
        loc = msg.location or {}
        u = loc.get("url") or ""
        buf["console_errors"].append({
            "text": text,
            "url": u,
            "line": loc.get("lineNumber"),
            "third_party": _is_third_party(text, u, host),
        })

    def on_pageerror(exc):
        buf["page_errors"].append(str(exc)[:500])

    def on_response(resp):
        try:
            status = resp.status
            if status < 400:
                return
            u = resp.url
            netloc = urlparse(u).netloc
            path = urlparse(u).path
            buf["failed_responses"].append({
                "url": u[:300],
                "status": status,
                "method": resp.request.method,
                "same_origin": netloc == host,
                "is_api": "/api/" in path,
            })
        except Exception:
            pass

    def on_requestfailed(req):
        try:
            u = req.url
            netloc = urlparse(u).netloc
            path = urlparse(u).path
            buf["failed_responses"].append({
                "url": u[:300],
                "status": None,
                "failure": (req.failure or "")[:200],
                "method": req.method,
                "same_origin": netloc == host,
                "is_api": "/api/" in path,
            })
        except Exception:
            pass

    page.on("console", on_console)
    page.on("pageerror", on_pageerror)
    page.on("response", on_response)
    page.on("requestfailed", on_requestfailed)
    return buf


def _classify(route_result: dict) -> str:
    """Bucket a route's findings: critical | high | medium | clean.

    App/API failures and app-origin JS errors are load-bearing; third-party
    console/network noise is capped at medium so it never alerts."""
    if route_result["page_errors"] or route_result["nav_error"]:
        return "critical"
    fr = route_result["failed_responses"]
    app_fr = [f for f in fr if f.get("same_origin") or f.get("is_api")]
    if any((f.get("status") or 500) >= 500 for f in app_fr):
        return "critical"
    app_console = [c for c in route_result["console_errors"] if not c.get("third_party")]
    if app_fr or app_console or route_result["selector_misses"]:
        return "high"
    visual_diff = route_result.get("visual_diff") or {}
    if visual_diff.get("status") == "changed":
        return "high"
    a11y_issues = route_result.get("a11y_issues") or []
    if any((i.get("severity") or 0) >= 3 for i in a11y_issues):
        return "high"
    if visual_diff.get("status") == "error" or a11y_issues:
        return "medium"
    if fr or route_result["console_errors"]:
        return "medium"
    return "clean"


# ---- per-route walk -------------------------------------------------------

def _qa_entry(
    context,
    entry: spec.Entry,
    *,
    base_url: str,
    host: str,
    run_dir: Path,
    ready_selector: str | None = None,
    a11y_enabled: bool = True,
    visual_baseline: Path | None = None,
    update_baseline: bool = False,
    visual_threshold: float = 0.01,
) -> dict:
    started = time.time()
    page = context.new_page()
    page.set_default_timeout(15_000)
    page.set_default_navigation_timeout(30_000)
    buf = _attach_listeners(page, host)
    nav_error = None
    selector_misses: list[dict] = []
    a11y_issues: list[dict] = []
    visual_diff: dict | None = None
    shot_rel = None
    try:
        actions_log, _panel_bbox, nav_error = record._drive_entry(
            page, entry, base_url=base_url, cdp=None, ready_selector=ready_selector,
        )
        selector_misses = [
            {"selector": a.get("selector"), "reason": a.get("reason")}
            for a in actions_log if a.get("skipped")
        ]
        shot = run_dir / "screenshots" / f"{entry.id}.png"
        page.screenshot(path=str(shot), full_page=False)
        shot_rel = str(shot.relative_to(run_dir))
        if a11y_enabled:
            a11y_issues = a11y.scan(page)
        if visual_baseline:
            visual_diff = visual.compare_or_update(
                shot,
                entry_id=entry.id,
                baseline_dir=visual_baseline,
                run_dir=run_dir,
                update=update_baseline,
                threshold=visual_threshold,
            )
        final_url = page.url
    except Exception as exc:
        nav_error = nav_error or f"{type(exc).__name__}: {exc}"
        final_url = None
    finally:
        with contextlib.suppress(Exception):
            page.close()

    result = {
        "id": entry.id,
        "route": entry.route,
        "final_url": final_url,
        "screenshot": shot_rel,
        "nav_error": nav_error,
        "console_errors": buf["console_errors"],
        "page_errors": buf["page_errors"],
        "failed_responses": buf["failed_responses"],
        "selector_misses": selector_misses,
        "a11y_issues": a11y_issues,
        "visual_diff": visual_diff,
        "elapsed_ms": int((time.time() - started) * 1000),
    }
    result["severity"] = _classify(result)
    return result


# ---- reporting ------------------------------------------------------------

_ORDER = {"critical": 0, "high": 1, "medium": 2, "clean": 3}


def _write_report(run_dir: Path, meta: dict, results: list[dict]) -> str:
    by_sev: dict[str, list] = {"critical": [], "high": [], "medium": [], "clean": []}
    for r in results:
        by_sev[r["severity"]].append(r)

    lines = [
        f"# {meta['report_name']} - {meta['target_label']} - {meta['generated_at']}",
        "",
        f"Target: `{meta['base_url']}`  -  routes: {len(results)}  -  "
        f"crit {len(by_sev['critical'])} / high {len(by_sev['high'])} / "
        f"med {len(by_sev['medium'])} / clean {len(by_sev['clean'])}",
        "",
    ]
    for sev in ("critical", "high", "medium"):
        if not by_sev[sev]:
            continue
        lines.append(f"## {sev.upper()}")
        for r in sorted(by_sev[sev], key=lambda x: x["route"]):
            lines.append(f"### `{r['route']}` ({r['id']})")
            if r["nav_error"]:
                lines.append(f"- **nav**: {r['nav_error']}")
            for pe in r["page_errors"]:
                lines.append(f"- **JS exception**: {pe}")
            for ce in r["console_errors"][:5]:
                lines.append(f"- console.error: {ce['text']}")
            for f in r["failed_responses"][:8]:
                tag = "API" if f.get("is_api") else ("app" if f.get("same_origin") else "3p")
                st = f.get("status") or f.get("failure") or "failed"
                lines.append(f"- [{tag}] {f['method']} {st} - {f['url']}")
            for sm in r["selector_misses"]:
                lines.append(f"- selector miss: `{sm['selector']}`")
            vd = r.get("visual_diff") or {}
            if vd and vd.get("status") not in ("unchanged", "updated", "baseline_created"):
                pct = (vd.get("mismatch_ratio") or 0) * 100
                lines.append(f"- visual diff: {vd.get('status')} ({pct:.2f}% mismatch)")
                if vd.get("reason"):
                    lines.append(f"  - {vd['reason']}")
                if vd.get("diff"):
                    lines.append(f"  - diff: `{vd['diff']}`")
            for issue in (r.get("a11y_issues") or [])[:10]:
                lines.append(
                    f"- a11y[{issue.get('severity', '?')}] {issue.get('rule')}: "
                    f"{issue.get('message')} (`{issue.get('selector')}`)"
                )
            if r["screenshot"]:
                lines.append(f"- shot: `{r['screenshot']}`")
            lines.append("")
    report = "\n".join(lines)
    (run_dir / "report.md").write_text(report)

    crit, high, med = len(by_sev["critical"]), len(by_sev["high"]), len(by_sev["medium"])
    if crit:
        digest = f"UX-QA {meta['target_label']}: {crit} critical, {high} high across {len(results)} routes"
    elif high:
        digest = f"UX-QA {meta['target_label']}: {high} high across {len(results)} routes"
    elif med:
        digest = f"UX-QA {meta['target_label']}: {med} medium across {len(results)} routes"
    else:
        digest = f"UX-QA {meta['target_label']}: clean across {len(results)} routes"
    (run_dir / "digest-line.txt").write_text(digest + "\n")
    return digest


def _print_table(results: list[dict]) -> None:
    color = {"critical": "\033[31m", "high": "\033[33m", "medium": "\033[2m", "clean": "\033[32m"}
    reset = "\033[0m"
    for r in sorted(results, key=lambda x: (_ORDER[x["severity"]], x["route"])):
        c = color[r["severity"]]
        n = (len(r["page_errors"]) + len(r["console_errors"])
             + len(r["failed_responses"]) + len(r["selector_misses"])
             + len(r.get("a11y_issues") or []))
        vd = r.get("visual_diff") or {}
        if vd.get("status") == "changed":
            n += 1
        flag = "!" if r["nav_error"] else " "
        sys.stdout.write(
            f"  {c}{r['severity']:<8}{reset}{flag} {r['route']:<38} "
            f"{n:>2} signals  {r['elapsed_ms']:>5}ms\n"
        )


# ---- main -----------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spec", default=str(THIS_DIR / "docs-spec.yaml"))
    ap.add_argument("--env-file", help="site env file (default: UXQA_ENV_FILE or ~/.uxqa/default.env)")
    ap.add_argument("--base-url", help="override UXQA_BASE_URL (e.g. a preview deploy)")
    ap.add_argument("--login-url", help="override UXQA_LOGIN_URL")
    ap.add_argument("--target-label", default=None, help="label for the report (prod/preview/<branch>)")
    ap.add_argument("--only", help="run a single entry id")
    ap.add_argument("--limit", type=int, help="run only the first N routes (smoke test)")
    ap.add_argument("--headed", action="store_true", help="show browser (no xvfb)")
    ap.add_argument("--a11y", dest="a11y", action="store_true", default=None,
                    help="enable deterministic accessibility scan")
    ap.add_argument("--no-a11y", dest="a11y", action="store_false",
                    help="disable deterministic accessibility scan")
    ap.add_argument("--visual-baseline", help="directory of baseline screenshots")
    ap.add_argument("--update-baseline", action="store_true",
                    help="write current screenshots into the visual baseline directory")
    ap.add_argument("--visual-threshold", type=float,
                    help="max changed-pixel ratio before visual diff is high severity")
    args = ap.parse_args()

    cfg = env.load(args.env_file)
    if args.base_url:
        cfg["UXQA_BASE_URL"] = args.base_url
    if args.login_url:
        cfg["UXQA_LOGIN_URL"] = args.login_url
    env.require(cfg, "UXQA_BASE_URL")
    base_url = cfg["UXQA_BASE_URL"].rstrip("/")
    login_url = cfg.get("UXQA_LOGIN_URL")
    host = urlparse(base_url).netloc
    ready_selector = cfg.get("UXQA_READY_SELECTOR")
    target_label = args.target_label or ("preview" if args.base_url else "prod")
    a11y_enabled = args.a11y
    if a11y_enabled is None:
        a11y_enabled = cfg.get("UXQA_A11Y", "1").lower() not in ("0", "false", "no")
    visual_baseline = args.visual_baseline or cfg.get("UXQA_VISUAL_BASELINE")
    visual_baseline_path = Path(visual_baseline).expanduser() if visual_baseline else None
    visual_threshold = (
        args.visual_threshold
        if args.visual_threshold is not None
        else float(cfg.get("UXQA_VISUAL_THRESHOLD", "0.01"))
    )

    entries, issues = spec.load(Path(args.spec))
    # QA does not narrate - voice-gate issues are irrelevant here; only surface
    # structural problems (load() already raises on those).
    for i in issues:
        if i.severity == "error" and "voice-gate" not in i.message and "narration" not in i.message:
            sys.stderr.write(f"[spec] {i.entry_id}: {i.message}\n")
    if args.only:
        entries = [e for e in entries if e.id == args.only]
        if not entries:
            ap.error(f"no entry with id={args.only}")
    if args.limit:
        entries = entries[: args.limit]

    run_dir = record._new_run_dir("qa")
    meta = {
        "generated_at": dt.datetime.now(dt.UTC).replace(tzinfo=None).isoformat() + "Z",
        "base_url": base_url,
        "target_label": target_label,
        "report_name": cfg.get("UXQA_REPORT_NAME", "UX-QA"),
        "route_count": len(entries),
        "run_dir": str(run_dir),
        "a11y_enabled": a11y_enabled,
        "visual_baseline": str(visual_baseline_path) if visual_baseline_path else None,
        "visual_threshold": visual_threshold,
    }

    ctx = record._xvfb_if_needed() if not args.headed else contextlib.nullcontext()
    results: list[dict] = []
    with ctx, sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        context_kwargs = {"viewport": record.VIEWPORT}
        cached = auth.storage_state_path(cfg.get("UXQA_STORAGE_STATE"))
        if cached:
            context_kwargs["storage_state"] = cached
        context = browser.new_context(**context_kwargs)
        try:
            auth.ensure_ready(
                context,
                base_url=base_url,
                login_url=login_url,
                mode=cfg.get("UXQA_AUTH_MODE", "public"),
                email=cfg.get("UXQA_AUTH_EMAIL"),
                password=cfg.get("UXQA_AUTH_PASSWORD"),
                ready_selector=ready_selector,
                storage_state=cfg.get("UXQA_STORAGE_STATE"),
            )
            for entry in entries:
                try:
                    results.append(
                        _qa_entry(
                            context,
                            entry,
                            base_url=base_url,
                            host=host,
                            run_dir=run_dir,
                            ready_selector=ready_selector,
                            a11y_enabled=a11y_enabled,
                            visual_baseline=visual_baseline_path,
                            update_baseline=args.update_baseline,
                            visual_threshold=visual_threshold,
                        )
                    )
                except Exception as exc:
                    results.append({
                        "id": entry.id, "route": entry.route, "final_url": None,
                        "screenshot": None, "nav_error": f"{type(exc).__name__}: {exc}",
                        "console_errors": [], "page_errors": [], "failed_responses": [],
                        "selector_misses": [], "a11y_issues": [], "visual_diff": None,
                        "elapsed_ms": 0, "severity": "critical",
                        "trace": traceback.format_exc(limit=3),
                    })
        finally:
            with contextlib.suppress(Exception):
                context.close()
            with contextlib.suppress(Exception):
                browser.close()

    manifest = {**meta, "results": results}
    (run_dir / "qa-manifest.json").write_text(json.dumps(manifest, indent=2))
    digest = _write_report(run_dir, meta, results)

    _print_table(results)
    sys.stdout.write(f"\n{digest}\n")
    sys.stdout.write(f"manifest: {run_dir / 'qa-manifest.json'}\n")
    sys.stdout.write(f"report:   {run_dir / 'report.md'}\n")

    crit = sum(1 for r in results if r["severity"] == "critical")
    return 1 if crit else 0


if __name__ == "__main__":
    sys.exit(main())
