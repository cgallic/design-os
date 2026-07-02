"""Verify every editable sibling dependency imports cleanly."""
import sys


def verify() -> list[str]:
    """Return a list of failure messages; empty list means all deps import."""
    failures = []
    checks = [
        ("approval_inbox", "ApprovalStore"),
        ("cmo_dashboard", None),
    ]
    for module_name, attr in checks:
        try:
            module = __import__(module_name)
        except ImportError as exc:
            failures.append(f"{module_name}: import failed ({exc})")
            continue
        if attr is not None and not hasattr(module, attr):
            failures.append(f"{module_name}: missing expected attribute {attr!r}")
    return failures


if __name__ == "__main__":
    problems = verify()
    if problems:
        for p in problems:
            print(f"FAIL: {p}", file=sys.stderr)
        sys.exit(1)
    print("All sibling dependencies import cleanly.")
