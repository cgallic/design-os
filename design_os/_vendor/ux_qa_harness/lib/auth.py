"""Authentication adapters for UX-QA Harness.

Supported modes:
- public: no login; useful for public WordPress/Case Engine pages.
- form: generic email/password form.
- wordpress: wp-login.php form with log/pwd fields.
"""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import BrowserContext, Page, TimeoutError as PWTimeout


def storage_state_path(path: str | None = None) -> str | None:
    if not path:
        return None
    p = Path(path).expanduser()
    return str(p) if p.exists() else None


def _dismiss_cookie_banner(page: Page) -> None:
    candidates = [
        "button:has-text('Essential only')",
        "button:has-text('Accept all')",
        "button:has-text('Reject all')",
        "button:has-text('Accept')",
        "button:has-text('I agree')",
    ]
    for sel in candidates:
        try:
            loc = page.locator(sel).first
            if loc.count() and loc.is_visible():
                loc.click(timeout=2_000)
                page.wait_for_timeout(250)
                return
        except Exception:
            continue


def _remove_common_overlays(page: Page) -> None:
    try:
        page.evaluate(
            """() => document.querySelectorAll(
                '[role=dialog], .cookie-banner, [class*=cookie], [class*=consent]'
            ).forEach(e => e.remove())"""
        )
    except Exception:
        pass


def _ready(page: Page, selector: str | None) -> bool:
    if not selector:
        return True
    try:
        page.locator(selector).first.wait_for(state="visible", timeout=15_000)
        return True
    except PWTimeout:
        return False


def _generic_form_login(page: Page, email: str, password: str) -> None:
    email_input = page.locator(
        "input[type='email'], input[name='email'], input[autocomplete='email'], input[name='log']"
    ).first
    pwd_input = page.locator(
        "input[type='password'], input[name='password'], input[autocomplete='current-password'], input[name='pwd']"
    ).first
    email_input.wait_for(state="visible", timeout=15_000)
    email_input.fill(email)
    pwd_input.fill(password)
    for sel in (
        "button[type='submit']",
        "input[type='submit']",
        "button:has-text('Sign in')",
        "button:has-text('Log in')",
    ):
        loc = page.locator(sel).first
        try:
            if loc.count() and loc.is_visible():
                loc.click(timeout=3_000)
                return
        except Exception:
            continue
    pwd_input.press("Enter")


def ensure_ready(
    context: BrowserContext,
    *,
    base_url: str,
    login_url: str | None = None,
    mode: str = "public",
    email: str | None = None,
    password: str | None = None,
    ready_selector: str | None = None,
    storage_state: str | None = None,
) -> Page:
    """Open a page and ensure it is ready for route crawling."""
    page = context.new_page()
    page.set_default_timeout(20_000)
    page.set_default_navigation_timeout(30_000)

    base = base_url.rstrip("/")
    mode = (mode or "public").lower()

    if mode == "public":
        page.goto(base, wait_until="domcontentloaded")
        _dismiss_cookie_banner(page)
        return page

    if not login_url:
        if mode == "wordpress":
            login_url = f"{base}/wp-login.php"
        else:
            login_url = f"{base}/login"
    if not email or not password:
        raise RuntimeError(f"auth mode {mode!r} requires UXQA_AUTH_EMAIL and UXQA_AUTH_PASSWORD")

    page.goto(base, wait_until="domcontentloaded")
    _dismiss_cookie_banner(page)
    if _ready(page, ready_selector):
        return page

    page.goto(login_url, wait_until="domcontentloaded")
    _dismiss_cookie_banner(page)
    _remove_common_overlays(page)
    _generic_form_login(page, email, password)
    page.wait_for_load_state("domcontentloaded", timeout=30_000)
    try:
        page.wait_for_load_state("networkidle", timeout=15_000)
    except PWTimeout:
        pass
    _dismiss_cookie_banner(page)
    _remove_common_overlays(page)

    if ready_selector and not _ready(page, ready_selector):
        raise RuntimeError(f"ready selector did not render after login: {ready_selector}")

    if storage_state:
        target = Path(storage_state).expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        context.storage_state(path=str(target))
    return page
