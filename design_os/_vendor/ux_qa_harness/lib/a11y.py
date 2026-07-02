"""Small deterministic accessibility scan for pages driven by qa.py.

This is not a replacement for axe-core. It catches high-signal issues that are
cheap to detect in any browser context and useful in nightly QA reports.
"""
from __future__ import annotations

from typing import Any


SCAN_JS = r"""
() => {
  const issues = [];
  const visible = (el) => {
    const style = window.getComputedStyle(el);
    const box = el.getBoundingClientRect();
    return style.visibility !== 'hidden' && style.display !== 'none' &&
      box.width > 0 && box.height > 0;
  };
  const labelText = (el) => {
    const bits = [];
    const id = el.getAttribute('id');
    if (id) {
      document.querySelectorAll(`label[for="${CSS.escape(id)}"]`).forEach(label => {
        bits.push(label.textContent || '');
      });
    }
    const parentLabel = el.closest('label');
    if (parentLabel) bits.push(parentLabel.textContent || '');
    ['aria-label', 'aria-labelledby', 'title', 'placeholder', 'name', 'alt'].forEach(attr => {
      const val = el.getAttribute(attr);
      if (val) bits.push(val);
    });
    const labelledBy = el.getAttribute('aria-labelledby');
    if (labelledBy) {
      labelledBy.split(/\s+/).forEach(ref => {
        const target = document.getElementById(ref);
        if (target) bits.push(target.textContent || '');
      });
    }
    return bits.join(' ').replace(/\s+/g, ' ').trim();
  };
  const cssPath = (el) => {
    if (el.id) return `#${el.id}`;
    const parts = [];
    let cur = el;
    while (cur && cur.nodeType === 1 && parts.length < 4) {
      let part = cur.tagName.toLowerCase();
      const cls = String(cur.className || '').trim().split(/\s+/).filter(Boolean)[0];
      if (cls) part += `.${cls}`;
      parts.unshift(part);
      cur = cur.parentElement;
    }
    return parts.join(' > ');
  };
  const add = (rule, severity, selector, message) => {
    issues.push({rule, severity, selector, message});
  };

  if (!document.title || !document.title.trim()) {
    add('document-title', 2, 'title', 'Document has no title.');
  }
  const lang = document.documentElement.getAttribute('lang');
  if (!lang || !lang.trim()) {
    add('html-lang', 2, 'html', 'HTML element has no lang attribute.');
  }

  const ids = new Map();
  document.querySelectorAll('[id]').forEach(el => {
    const id = el.getAttribute('id');
    if (!id) return;
    ids.set(id, (ids.get(id) || 0) + 1);
  });
  ids.forEach((count, id) => {
    if (count > 1) add('duplicate-id', 3, `#${id}`, `Duplicate id "${id}" appears ${count} times.`);
  });

  document.querySelectorAll('img').forEach(img => {
    if (!visible(img)) return;
    if (!img.hasAttribute('alt')) {
      add('image-alt', 2, cssPath(img), 'Visible image is missing alt text.');
    }
  });

  document.querySelectorAll('input, select, textarea').forEach(el => {
    const type = (el.getAttribute('type') || '').toLowerCase();
    if (type === 'hidden' || !visible(el)) return;
    if (!labelText(el)) {
      add('form-label', 3, cssPath(el), 'Visible form control has no accessible label.');
    }
  });

  document.querySelectorAll('button, a[href], [role="button"], [role="link"]').forEach(el => {
    if (!visible(el)) return;
    if (!labelText(el) && !(el.textContent || '').trim()) {
      add('accessible-name', 3, cssPath(el), 'Interactive element has no accessible name.');
    }
    const box = el.getBoundingClientRect();
    if ((box.width < 24 || box.height < 24) && (box.width > 0 && box.height > 0)) {
      add('target-size', 1, cssPath(el), 'Interactive target is smaller than 24px in one dimension.');
    }
  });

  let last = 0;
  document.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(h => {
    if (!visible(h)) return;
    const level = Number(h.tagName.slice(1));
    if (last && level > last + 1) {
      add('heading-order', 2, cssPath(h), `Heading jumps from h${last} to h${level}.`);
    }
    last = level;
  });

  document.querySelectorAll('[aria-hidden="true"]').forEach(el => {
    if (el.querySelector('a[href], button, input, select, textarea, [tabindex]:not([tabindex="-1"])')) {
      add('aria-hidden-focus', 3, cssPath(el), 'aria-hidden container includes focusable content.');
    }
  });

  return issues;
}
"""


def scan(page) -> list[dict[str, Any]]:
    try:
        issues = page.evaluate(SCAN_JS)
    except Exception as exc:
        return [{
            "rule": "a11y-scan-error",
            "severity": 1,
            "selector": "document",
            "message": f"Accessibility scan failed: {type(exc).__name__}: {exc}",
        }]
    return [i for i in issues if isinstance(i, dict)]
