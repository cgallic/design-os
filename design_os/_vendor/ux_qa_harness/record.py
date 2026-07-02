#!/usr/bin/env python3
"""UX-QA Harness recorder - drives a site from a spec and captures screenshots/video.

Phase 1: --dry-run produces 1 screenshot per spec entry, no video, no TTS.
Phase 2: --record produces 1 mp4 per entry + clip metadata sidecar (.json).

Usage:
  ./record.py --dry-run                   # screenshots only
  ./record.py --dry-run --only calls      # one entry by id
  ./record.py --record                    # full clip capture (Phase 2)
  ./record.py --explore                   # interactive route audit (no spec)

Run on a box with Playwright browsers installed. xvfb is required on headless Linux
when no DISPLAY exists.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

from playwright.sync_api import (
    BrowserContext,
    Page,
    sync_playwright,
    TimeoutError as PWTimeout,
)

# Local imports
THIS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(THIS_DIR))
from lib import auth, env, spec  # noqa: E402

VIEWPORT = {"width": 1920, "height": 1080}
DEFAULT_NAV_TIMEOUT = 30_000

# CSS injected once per page to host the persistent cursor dot + halo overlay.
# Keeps the cursor visible in page.video() output (Playwright headless doesn't
# render the OS cursor in screencasts).
_CURSOR_CSS = """
#__docs_cursor__ {
    position: fixed; left: -100px; top: -100px;
    width: 28px; height: 28px;
    border: 3px solid #4F46E5;
    background: rgba(79,70,229,0.35);
    border-radius: 50%;
    box-shadow: 0 0 0 4px rgba(79,70,229,0.18);
    pointer-events: none;
    z-index: 2147483647;
    transition: left 220ms cubic-bezier(.2,.8,.2,1), top 220ms cubic-bezier(.2,.8,.2,1),
                transform 120ms ease-out, opacity 220ms ease;
    transform: translate(-50%, -50%);
}
#__docs_cursor__.click { transform: translate(-50%, -50%) scale(0.65); background: rgba(79,70,229,0.6); }
.__docs_halo__ {
    position: fixed;
    border: 3px solid #4F46E5;
    border-radius: 12px;
    box-shadow: 0 0 0 6px rgba(79,70,229,0.22);
    pointer-events: none;
    z-index: 2147483646;
    transition: opacity 320ms ease;
}
"""


def _install_overlay(page: Page) -> None:
    """Inject cursor + halo overlay. Self-heals via MutationObserver because
    React hydration replaces body's children and would otherwise strip the
    cursor.

    Mounted on documentElement (html), not body, so React's body-tree
    diffing can't touch it. CSS is keyed in head so it survives too.
    """
    page.evaluate(
        """css => {
            const ensureStyle = () => {
                if (document.getElementById('__docs_cursor_style__')) return;
                const style = document.createElement('style');
                style.id = '__docs_cursor_style__';
                style.textContent = css;
                document.head.appendChild(style);
            };
            const ensureDot = () => {
                if (document.getElementById('__docs_cursor__')) return;
                const dot = document.createElement('div');
                dot.id = '__docs_cursor__';
                document.documentElement.appendChild(dot);
            };
            ensureStyle();
            ensureDot();
            if (window.__docs_obs__) return;
            window.__docs_obs__ = new MutationObserver(() => {
                ensureStyle();
                ensureDot();
            });
            window.__docs_obs__.observe(document.documentElement, {
                childList: true, subtree: true
            });
        }""",
        _CURSOR_CSS,
    )


def _move_cursor(page: Page, x: float, y: float, *, click: bool = False) -> None:
    page.evaluate(
        """({x, y, click}) => {
            const d = document.getElementById('__docs_cursor__');
            if (!d) return;
            d.style.left = x + 'px';
            d.style.top = y + 'px';
            if (click) {
                d.classList.add('click');
                setTimeout(() => d.classList.remove('click'), 200);
            }
        }""",
        {"x": x, "y": y, "click": click},
    )


def _runs_root() -> Path:
    root = Path(os.environ.get("UXQA_RUNTIME_ROOT", str(Path.home() / ".uxqa" / "runs"))).expanduser()
    if root.name == "runs":
        return root
    return root / "runs"


def _new_run_dir(mode: str) -> Path:
    stamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    run_dir = _runs_root() / f"{stamp}-{mode}"
    run_dir.mkdir(parents=True, exist_ok=True)
    for sub in ("screenshots", "clips", "logs"):
        (run_dir / sub).mkdir(exist_ok=True)
    return run_dir


@contextmanager
def _xvfb_if_needed():
    """Start Xvfb on :99 if no DISPLAY is set, kill on exit. Idempotent."""
    if os.environ.get("DISPLAY") or os.name == "nt" or shutil.which("Xvfb") is None:
        yield
        return
    proc = subprocess.Popen(
        ["Xvfb", ":99", "-screen", "0", "1920x1080x24", "-ac"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    os.environ["DISPLAY"] = ":99"
    time.sleep(0.5)
    try:
        yield
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()


def _execute_action(
    page: Page,
    action: spec.Action,
    run_log: list[dict],
    *,
    cdp=None,
) -> dict | None:
    """Execute one Playwright action. Returns optional bounding-box metadata."""
    bbox: dict | None = None
    started = time.time()
    if action.type == "goto":
        url = action.url or ""
        page.goto(url, wait_until="domcontentloaded")
    elif action.type == "click":
        loc = page.locator(action.selector).first
        loc.wait_for(state="visible", timeout=10_000)
        bbox = loc.bounding_box()
        if bbox:
            _move_cursor(page, bbox["x"] + bbox["width"] / 2, bbox["y"] + bbox["height"] / 2, click=True)
            if action.highlight:
                _flash(page, bbox, cdp=cdp)
        loc.click()
    elif action.type == "hover":
        loc = page.locator(action.selector).first
        loc.wait_for(state="visible", timeout=10_000)
        bbox = loc.bounding_box()
        if bbox:
            _move_cursor(page, bbox["x"] + bbox["width"] / 2, bbox["y"] + bbox["height"] / 2)
            if action.highlight:
                _flash(page, bbox, cdp=cdp)
        loc.hover()
    elif action.type == "type":
        loc = page.locator(action.selector).first
        loc.wait_for(state="visible", timeout=10_000)
        loc.fill(action.text or "")
    elif action.type == "press":
        page.keyboard.press(action.key or "Enter")
    elif action.type == "wait":
        time.sleep((action.delay_ms or 1000) / 1000.0)
    elif action.type == "scroll":
        page.mouse.wheel(0, int(action.delay_ms or 400))
    run_log.append(
        {
            "type": action.type,
            "selector": action.selector,
            "text": action.text,
            "url": action.url,
            "highlight": action.highlight,
            "bbox": bbox,
            "elapsed_ms": int((time.time() - started) * 1000),
        }
    )
    return bbox


def _flash(page: Page, bbox: dict, *, hold_ms: int = 900, cdp=None) -> None:
    """Draw a halo on a panel for `hold_ms`. Two parallel signals:
      1. CSS halo via injected DOM - captured cleanly by page.video()
      2. CDP `Overlay.highlightRect` - per the kickoff spec; visible to a
         human attached via DevTools, may or may not land in the screencast.
    """
    if cdp is not None:
        try:
            cdp.send(
                "Overlay.highlightRect",
                {
                    "x": int(bbox["x"]),
                    "y": int(bbox["y"]),
                    "width": int(bbox["width"]),
                    "height": int(bbox["height"]),
                    "color": {"r": 79, "g": 70, "b": 229, "a": 0.20},
                    "outlineColor": {"r": 79, "g": 70, "b": 229, "a": 1.0},
                },
            )
        except Exception:
            pass
    page.evaluate(
        """({x,y,w,h,hold}) => {
            const d = document.createElement('div');
            d.className = '__docs_halo__';
            d.style.left = (x-6) + 'px';
            d.style.top = (y-6) + 'px';
            d.style.width = (w+12) + 'px';
            d.style.height = (h+12) + 'px';
            document.body.appendChild(d);
            setTimeout(() => { d.style.opacity = '0'; setTimeout(() => d.remove(), 360); }, hold);
        }""",
        {"x": bbox["x"], "y": bbox["y"], "w": bbox["width"], "h": bbox["height"], "hold": hold_ms},
    )
    page.wait_for_timeout(hold_ms + 250)
    if cdp is not None:
        try:
            cdp.send("Overlay.hideHighlight", {})
        except Exception:
            pass


def _resolve_route(base_url: str, route: str) -> str:
    base = base_url.rstrip("/")
    if route.startswith("http"):
        return route
    return f"{base}{route}"


def _drive_entry(
    page: Page,
    entry: spec.Entry,
    *,
    base_url: str,
    cdp,
    ready_selector: str | None = None,
) -> tuple[list[dict], dict | None, str | None]:
    """Navigate + execute actions on `page`. Returns (actions_log, panel_bbox, err)."""
    target = _resolve_route(base_url, entry.route)
    actions_log: list[dict] = []
    panel_bbox: dict | None = None
    err: str | None = None
    page.goto(target, wait_until="domcontentloaded")
    try:
        page.wait_for_load_state("networkidle", timeout=5_000)
    except PWTimeout:
        pass
    route_ready = entry.ready_selector or ready_selector
    if route_ready:
        try:
            page.locator(route_ready).first.wait_for(state="visible", timeout=10_000)
        except PWTimeout:
            err = f"ready selector never rendered at {entry.route}: {route_ready}"
    page.wait_for_timeout(700)
    _install_overlay(page)
    for action in entry.actions:
        try:
            bbox = _execute_action(page, action, actions_log, cdp=cdp)
        except PWTimeout as ex:
            # A selector miss is recoverable - log it, fall through to a
            # `main` hover so the clip still gets a halo, and keep going.
            actions_log.append({
                "type": action.type, "selector": action.selector,
                "skipped": True, "reason": f"selector miss: {str(ex)[:120]}",
            })
            if action.type in ("hover", "click") and action.highlight:
                try:
                    fallback = page.locator("main").first
                    fb_bbox = fallback.bounding_box()
                    if fb_bbox:
                        # Trim to viewport so the halo doesn't span the entire page.
                        viewport_h = 1080
                        clipped = {
                            "x": fb_bbox["x"], "y": fb_bbox["y"],
                            "width": fb_bbox["width"],
                            "height": min(fb_bbox["height"], viewport_h - fb_bbox["y"]),
                        }
                        _move_cursor(page, clipped["x"] + clipped["width"] / 2,
                                     clipped["y"] + min(120, clipped["height"]) / 2)
                        _flash(page, clipped, hold_ms=700, cdp=cdp)
                        bbox = clipped
                except Exception:
                    bbox = None
            else:
                bbox = None
        if action.highlight and bbox and panel_bbox is None:
            panel_bbox = bbox
    page.wait_for_timeout(500)
    if entry.panel_selector and panel_bbox is None:
        try:
            panel_bbox = page.locator(entry.panel_selector).first.bounding_box()
        except Exception:
            pass
    return actions_log, panel_bbox, err


def _process_entry_dryrun(
    page: Page,
    entry: spec.Entry,
    *,
    base_url: str,
    run_dir: Path,
    ready_selector: str | None = None,
) -> dict:
    """Phase 1 path: reuse the auth'd page; screenshot only."""
    started = time.time()
    try:
        actions_log, panel_bbox, err = _drive_entry(
            page, entry, base_url=base_url, cdp=None, ready_selector=ready_selector
        )
        shot = run_dir / "screenshots" / f"{entry.id}.png"
        page.screenshot(path=str(shot), full_page=False)
        return {
            "id": entry.id, "route": entry.route, "ok": err is None,
            "url": page.url, "screenshot": str(shot.relative_to(run_dir)),
            "panel_bbox": panel_bbox, "actions_run": len(actions_log),
            "elapsed_ms": int((time.time() - started) * 1000), "error": err,
        }
    except Exception as exc:
        return {
            "id": entry.id, "route": entry.route, "ok": False, "url": page.url,
            "actions_run": 0, "elapsed_ms": int((time.time() - started) * 1000),
            "error": f"{type(exc).__name__}: {exc}",
            "trace": traceback.format_exc(limit=3),
        }


def _process_entry_record(
    context: BrowserContext,
    entry: spec.Entry,
    *,
    base_url: str,
    run_dir: Path,
    ready_selector: str | None = None,
) -> dict:
    """Phase 2 path: fresh page per entry -> unique video file -> rename + metadata."""
    started = time.time()
    page = context.new_page()
    page.set_default_timeout(20_000)
    page.set_default_navigation_timeout(30_000)
    cdp = None
    try:
        try:
            cdp = context.new_cdp_session(page)
            cdp.send("Overlay.enable", {})
        except Exception:
            cdp = None
        actions_log, panel_bbox, err = _drive_entry(
            page, entry, base_url=base_url, cdp=cdp, ready_selector=ready_selector,
        )
        shot = run_dir / "screenshots" / f"{entry.id}.png"
        page.screenshot(path=str(shot), full_page=False)
        # Capture the video file: must close page first to flush.
        video = page.video
        page.close()
        clip_dst = run_dir / "clips" / f"{entry.id}.mp4"
        webm_intermediate: Path | None = None
        if video is not None:
            try:
                src = Path(video.path())
                if src.exists():
                    # Playwright emits .webm; transcode to mp4 (h264+aac) so
                    # downstream ffmpeg concat/xfade works cleanly. Also trims
                    # to duration_target in the same pass to save a re-encode.
                    target = float(entry.duration_target or 0)
                    # Playwright records video-only. We add a silent stereo
                    # audio track at transcode time so downstream concat/mix
                    # filters always have an audio chain to operate on.
                    args = [
                        "ffmpeg", "-y", "-i", str(src),
                        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                    ]
                    if target > 0:
                        args += ["-t", f"{target}"]
                    args += [
                        "-map", "0:v:0", "-map", "1:a:0",
                        "-shortest",
                        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                        "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "160k",
                        "-movflags", "+faststart",
                        str(clip_dst),
                    ]
                    try:
                        subprocess.run(args, check=True, capture_output=True)
                        src.unlink(missing_ok=True)
                        webm_intermediate = src
                    except subprocess.CalledProcessError as ce:
                        err = err or f"ffmpeg transcode failed: {ce.stderr.decode()[-200:]}"
                else:
                    err = err or f"video file missing at {src}"
            except Exception as ve:
                err = err or f"video.path() failed: {ve}"
        else:
            err = err or "no video object on page (record_video_dir not set?)"
        meta = {
            "entry_id": entry.id,
            "route": entry.route,
            "url": page.url if not page.is_closed() else None,
            "duration_target": entry.duration_target,
            "actions_log": actions_log,
            "panel_bbox": panel_bbox,
            "screenshot": str(shot.relative_to(run_dir)),
            "clip": str(clip_dst.relative_to(run_dir)) if clip_dst.exists() else None,
            "captured_at": dt.datetime.utcnow().isoformat() + "Z",
        }
        (run_dir / "clips" / f"{entry.id}.json").write_text(json.dumps(meta, indent=2))
        return {
            "id": entry.id, "route": entry.route, "ok": err is None and clip_dst.exists(),
            "url": meta["url"], "screenshot": str(shot.relative_to(run_dir)),
            "clip": meta["clip"], "panel_bbox": panel_bbox,
            "actions_run": len(actions_log),
            "elapsed_ms": int((time.time() - started) * 1000), "error": err,
        }
    except Exception as exc:
        try:
            if not page.is_closed():
                page.close()
        except Exception:
            pass
        return {
            "id": entry.id, "route": entry.route, "ok": False,
            "url": None, "actions_run": 0,
            "elapsed_ms": int((time.time() - started) * 1000),
            "error": f"{type(exc).__name__}: {exc}",
            "trace": traceback.format_exc(limit=3),
        }
    finally:
        if cdp is not None:
            try:
                cdp.detach()
            except Exception:
                pass


def _print_table(results: list[dict]) -> None:
    """Green/red ascii table per the kickoff acceptance criteria."""
    GREEN = "\033[32m"
    RED = "\033[31m"
    DIM = "\033[2m"
    RESET = "\033[0m"
    rows = []
    for r in results:
        mark = f"{GREEN}OK {RESET}" if r["ok"] else f"{RED}FAIL{RESET}"
        bbox = r.get("panel_bbox")
        bbox_s = "-" if not bbox else f"{int(bbox['width'])}x{int(bbox['height'])}"
        clip = r.get("clip") or "-"
        rows.append(
            f"  {mark}  {r['id']:<22} {r['route']:<35} {r['actions_run']:>2}a  "
            f"{r['elapsed_ms']:>5}ms  panel={bbox_s:<14} clip={clip}"
        )
    sys.stdout.write("\n".join(rows) + "\n")
    fails = [r for r in results if not r["ok"]]
    if fails:
        sys.stdout.write(f"\n{RED}{len(fails)} failure(s):{RESET}\n")
        for r in fails:
            sys.stdout.write(f"  {r['id']}: {r.get('error')}\n")
            if r.get("trace"):
                sys.stdout.write(f"{DIM}{r['trace']}{RESET}\n")
    ok = len(results) - len(fails)
    sys.stdout.write(f"\n{ok}/{len(results)} entries passed.\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="screenshots only, no video")
    ap.add_argument("--record", action="store_true", help="enable page.video() capture (Phase 2)")
    ap.add_argument("--only", help="run a single entry id")
    ap.add_argument("--spec", default=str(THIS_DIR / "docs-spec.yaml"))
    ap.add_argument("--env-file", help="site env file (default: UXQA_ENV_FILE or ~/.uxqa/default.env)")
    ap.add_argument("--base-url", help="override UXQA_BASE_URL")
    ap.add_argument("--explore", action="store_true",
                    help="bypass spec - login + dump internal links for route discovery")
    ap.add_argument("--headed", action="store_true", help="show browser (no xvfb)")
    args = ap.parse_args()

    if not args.dry_run and not args.record and not args.explore:
        ap.error("pick one of --dry-run, --record, --explore")

    cfg = env.load(args.env_file)
    if args.base_url:
        cfg["UXQA_BASE_URL"] = args.base_url
    env.require(cfg, "UXQA_BASE_URL")
    base_url = cfg["UXQA_BASE_URL"].rstrip("/")
    ready_selector = cfg.get("UXQA_READY_SELECTOR")

    mode = "dryrun" if args.dry_run else ("record" if args.record else "explore")
    run_dir = _new_run_dir(mode)
    log_path = run_dir / "logs" / "run.json"

    entries: list[spec.Entry] = []
    if not args.explore:
        entries, issues = spec.load(Path(args.spec))
        # Structural spec errors should stop before driving the browser.
        gate_errors = [i for i in issues if i.severity == "error"]
        if gate_errors:
            sys.stderr.write("spec failures:\n")
            for i in gate_errors:
                sys.stderr.write(f"  {i.entry_id}: {i.message}\n")
            return 2
        for i in issues:
            sys.stderr.write(f"[spec warn] {i.entry_id}: {i.message}\n")

        if args.only:
            entries = [e for e in entries if e.id == args.only]
            if not entries:
                ap.error(f"no entry with id={args.only}")

    use_xvfb = not args.headed
    ctx = _xvfb_if_needed() if use_xvfb else _no_xvfb()
    with ctx, sync_playwright() as p:
        launch_opts = {"headless": False if args.headed else True}
        browser = p.chromium.launch(**launch_opts)
        context_kwargs = {"viewport": VIEWPORT}
        cached = auth.storage_state_path(cfg.get("UXQA_STORAGE_STATE"))
        if cached:
            context_kwargs["storage_state"] = cached
        if args.record:
            context_kwargs["record_video_dir"] = str(run_dir / "clips")
            context_kwargs["record_video_size"] = VIEWPORT
        context = browser.new_context(**context_kwargs)
        try:
            login_page = auth.ensure_ready(
                context,
                base_url=base_url,
                login_url=cfg.get("UXQA_LOGIN_URL"),
                mode=cfg.get("UXQA_AUTH_MODE", "public"),
                email=cfg.get("UXQA_AUTH_EMAIL"),
                password=cfg.get("UXQA_AUTH_PASSWORD"),
                ready_selector=ready_selector,
                storage_state=cfg.get("UXQA_STORAGE_STATE"),
            )

            if args.explore:
                rc = _explore(context, base_url, run_dir)
                return rc

            results: list[dict] = []
            if args.record:
                # Phase 2: each entry gets its own page -> its own video file.
                # The login_page's video lands in record_video_dir too - close
                # it so its file flushes, then list and delete pre-entry leftovers.
                try:
                    login_video_path = login_page.video.path() if login_page.video else None
                except Exception:
                    login_video_path = None
                try:
                    login_page.close()
                except Exception:
                    pass
                # Wait briefly for the auth video to flush to disk so cleanup
                # can find it.
                time.sleep(0.5)
                pre_existing = set((run_dir / "clips").glob("*.webm")) | set(
                    (run_dir / "clips").glob("*.mp4")
                )

                for entry in entries:
                    results.append(
                        _process_entry_record(
                            context, entry,
                            base_url=base_url, run_dir=run_dir, ready_selector=ready_selector,
                        )
                    )
                # Sweep up the auth-page video + any orphaned recordings that
                # don't match an entry-id name pattern.
                entry_ids = {e.id for e in entries}
                for vid in (run_dir / "clips").glob("*.webm"):
                    if vid.stem not in entry_ids:
                        vid.unlink(missing_ok=True)
            else:
                # Dry-run: reuse the auth'd page.
                for entry in entries:
                    results.append(
                        _process_entry_dryrun(
                            login_page, entry,
                            base_url=base_url, run_dir=run_dir, ready_selector=ready_selector,
                        )
                    )
        finally:
            try:
                context.close()
            except Exception:
                pass
            browser.close()

    log_path.write_text(json.dumps(results, indent=2, default=str))
    _print_table(results)
    return 0 if all(r["ok"] for r in results) else 1


@contextmanager
def _no_xvfb():
    yield


def _explore(context: BrowserContext, base_url: str, run_dir: Path) -> int:
    """Open base URL, dump every same-origin nav link to JSON for audit."""
    page = context.pages[0] if context.pages else context.new_page()
    page.goto(base_url.rstrip("/"), wait_until="domcontentloaded")
    try:
        page.wait_for_load_state("networkidle", timeout=15_000)
    except PWTimeout:
        pass
    routes = sorted(
        set(
            page.evaluate(
                """() => Array.from(document.querySelectorAll('a[href]'))
                          .map(a => a.getAttribute('href'))
                          .filter(Boolean)
                          .filter(h => h.startsWith('/') && !h.startsWith('//'))"""
            )
        )
    )
    out = run_dir / "logs" / "explore_routes.json"
    out.write_text(json.dumps(routes, indent=2))
    sys.stdout.write(f"discovered {len(routes)} routes - saved to {out}\n")
    for r in routes:
        sys.stdout.write(f"  {r}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
