from scripts.verify_deps import verify


def test_verify_deps_reports_no_failures():
    problems = verify()
    assert problems == [], f"Dependency import failures: {problems}"
