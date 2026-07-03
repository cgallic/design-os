"""Extract a style snapshot from a live page with Playwright.

This is the only module that touches a browser; everything downstream
(checks.py, engine.py) operates on the plain-dict snapshot it returns, so the
whole lint layer is testable from a fixture file.

Snapshot schema (all keys always present):
{
  "url": str,
  "viewport": {"width": int, "height": int},
  "text_styles": [{"selector", "font_family", "font_size_px", "font_weight",
                   "line_height_px", "color", "background_color",
                   "chars_per_line", "is_large_text", "sample_text"}],
  "font_families": [str],       # distinct font-family stacks in use
  "font_sizes_px": [float],     # distinct sizes in use
  "colors": {"all": [str]},     # distinct computed colors (text + backgrounds + borders)
  "spacings_px": [float],       # observed margins/paddings/gaps > 0
  "interactive_targets": [{"selector", "width", "height"}],
  "headings": [{"level", "text", "font_size_px"}],
  "images_missing_alt": int,
  "animations": [{"selector", "duration_ms", "timing_function", "property"}],
}
"""
from __future__ import annotations

import json
from pathlib import Path

_EXTRACT_JS = r"""
() => {
  const cssPath = (el) => {
    const bits = [];
    let node = el;
    for (let depth = 0; node && node.nodeType === 1 && depth < 4; depth++) {
      let bit = node.tagName.toLowerCase();
      if (node.id) { bits.unshift(bit + '#' + node.id); break; }
      if (node.classList.length) bit += '.' + node.classList[0];
      bits.unshift(bit);
      node = node.parentElement;
    }
    return bits.join(' > ');
  };
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && s.opacity !== '0';
  };
  // Walk up for the first non-transparent background.
  const effectiveBg = (el) => {
    let node = el;
    while (node && node.nodeType === 1) {
      const bg = getComputedStyle(node).backgroundColor;
      if (bg && !bg.startsWith('rgba(0, 0, 0, 0)') && bg !== 'transparent') return bg;
      node = node.parentElement;
    }
    return 'rgb(255, 255, 255)';
  };

  const textStyles = [], fontFamilies = new Set(), fontSizes = new Set(), colors = new Set();
  const spacings = new Set(), headings = [], animations = [];

  const all = Array.from(document.querySelectorAll('body *')).filter(visible);
  for (const el of all.slice(0, 3000)) {
    const s = getComputedStyle(el);
    const ownText = Array.from(el.childNodes)
      .filter(n => n.nodeType === 3).map(n => n.textContent).join(' ').trim();

    if (ownText.length > 0) {
      const sizePx = parseFloat(s.fontSize);
      const weight = parseInt(s.fontWeight, 10) || 400;
      const lineHeightPx = s.lineHeight === 'normal' ? sizePx * 1.2 : parseFloat(s.lineHeight);
      const rect = el.getBoundingClientRect();
      const avgCharW = sizePx * 0.5;  // crude but stable approximation
      fontFamilies.add(s.fontFamily);
      fontSizes.add(Math.round(sizePx * 2) / 2);
      colors.add(s.color);
      textStyles.push({
        selector: cssPath(el),
        font_family: s.fontFamily,
        font_size_px: sizePx,
        font_weight: weight,
        line_height_px: lineHeightPx,
        color: s.color,
        background_color: effectiveBg(el),
        chars_per_line: ownText.length > 0 ? Math.round(rect.width / avgCharW) : null,
        is_large_text: sizePx >= 24 || (sizePx >= 18.66 && weight >= 700),
        sample_text: ownText.slice(0, 200),
      });
    }

    const bg = s.backgroundColor;
    if (bg && !bg.startsWith('rgba(0, 0, 0, 0)') && bg !== 'transparent') colors.add(bg);
    if (s.borderTopWidth !== '0px' && s.borderTopColor) colors.add(s.borderTopColor);

    for (const prop of ['marginTop','marginBottom','marginLeft','marginRight',
                        'paddingTop','paddingBottom','paddingLeft','paddingRight','rowGap','columnGap']) {
      const v = parseFloat(s[prop]);
      if (v > 0 && Number.isFinite(v)) spacings.add(Math.round(v * 10) / 10);
    }

    const dur = parseFloat(s.transitionDuration) * 1000;
    if (dur > 0 && s.transitionProperty !== 'none') {
      animations.push({ selector: cssPath(el), duration_ms: dur,
                        timing_function: s.transitionTimingFunction, property: s.transitionProperty });
    }
  }

  for (const h of document.querySelectorAll('h1,h2,h3,h4,h5,h6')) {
    if (!visible(h)) continue;
    headings.push({ level: parseInt(h.tagName[1], 10), text: (h.textContent || '').trim().slice(0, 80),
                    font_size_px: parseFloat(getComputedStyle(h).fontSize) });
  }

  const interactive = [];
  for (const el of document.querySelectorAll('a,button,input,select,textarea,[role=button],[onclick]')) {
    if (!visible(el)) continue;
    const r = el.getBoundingClientRect();
    interactive.push({ selector: cssPath(el), width: r.width, height: r.height });
  }

  let missingAlt = 0;
  for (const img of document.querySelectorAll('img')) {
    if (!visible(img)) continue;
    if (!img.hasAttribute('alt') && img.getAttribute('role') !== 'presentation') missingAlt++;
  }

  return {
    text_styles: textStyles.slice(0, 500),
    font_families: Array.from(fontFamilies),
    font_sizes_px: Array.from(fontSizes),
    colors: { all: Array.from(colors).slice(0, 300) },
    spacings_px: Array.from(spacings),
    interactive_targets: interactive.slice(0, 300),
    headings,
    images_missing_alt: missingAlt,
    animations: animations.slice(0, 100),
  };
}
"""


def extract_style_snapshot(url: str, viewport: dict | None = None, timeout_ms: int = 30000) -> dict:
    """Render url in headless Chromium and return the style snapshot dict."""
    from playwright.sync_api import sync_playwright

    viewport = viewport or {"width": 1440, "height": 900}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        try:
            page = browser.new_page(viewport=viewport)
            page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            data = page.evaluate(_EXTRACT_JS)
        finally:
            browser.close()
    data["url"] = url
    data["viewport"] = viewport
    return data


def write_snapshot(snapshot: dict, path: Path) -> Path:
    path = Path(path)
    path.write_text(json.dumps(snapshot, indent=1), encoding="utf-8")
    return path
