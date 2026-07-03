import pytest

from design_os.process.protocol import ProcessError, validate_process_log


def _good_log():
    return {
        "target": "kaicalls-homepage",
        "stages": {
            "brief": {
                "problem": "Trial signups stall on the pricing page.",
                "audience": "Solo founders comparing call-tracking tools.",
                "constraints": [
                    "Pricing table renders fully at 375px with no horizontal scroll",
                    "Primary CTA appears within the first viewport at 1440x900",
                    "No more than 2 typefaces on the page",
                ],
            },
            "divergence": {
                "directions": [
                    {"name": "ledger", "premise": "price as an itemized receipt", "artifact": "a.png"},
                    {"name": "slider", "premise": "cost scales live with call volume", "artifact": "b.png"},
                    {"name": "story", "premise": "price framed against one recovered lead", "artifact": "c.png"},
                ]
            },
            "convergence": {
                "chosen": "slider",
                "why": "Volume-anchored pricing tested clearest in copy review.",
                "killed": [
                    {"name": "ledger", "why": "reads as an invoice; wrong emotion"},
                    {"name": "story", "why": "buries the number people came for"},
                ],
            },
            "build": {
                "tokens_source": "brand-packs/kaicalls/tokens.json",
                "components_reused": ["Card", "Slider"],
                "components_invented": ["VolumeDial"],
                "invention_reasons": {"VolumeDial": "no existing input communicates logarithmic call volume"},
            },
            "self_lint": {"snapshot": "runs/x/style-snapshot.json", "unwaived_block_failures": 0},
            "critique": {"lenses_run": ["structure", "craft", "brand"], "verdicts": "runs/x/verdicts.json", "fails_addressed": True},
        },
    }


def test_good_log_passes_all_stages():
    results = validate_process_log(_good_log())
    assert all(r.ok for r in results), [r.problems for r in results if not r.ok]


def test_missing_stage_fails():
    log = _good_log()
    del log["stages"]["divergence"]
    results = {r.stage: r for r in validate_process_log(log)}
    assert not results["divergence"].ok


def test_adjective_constraint_without_checkable_core_fails():
    log = _good_log()
    log["stages"]["brief"]["constraints"] = ["make it clean and modern", "look premium", "feel fresh"]
    results = {r.stage: r for r in validate_process_log(log)}
    assert not results["brief"].ok
    assert any("banned adjective" in p for p in results["brief"].problems)


def test_adjective_with_checkable_core_is_fine():
    log = _good_log()
    log["stages"]["brief"]["constraints"] = [
        "clean layout: every spacing value on the 8px grid",
        "modern type: body text at least 16px",
        "CTA visible within first viewport at 1440x900",
    ]
    results = {r.stage: r for r in validate_process_log(log)}
    assert results["brief"].ok, results["brief"].problems


def test_two_directions_is_not_divergence():
    log = _good_log()
    log["stages"]["divergence"]["directions"] = log["stages"]["divergence"]["directions"][:2]
    results = {r.stage: r for r in validate_process_log(log)}
    assert not results["divergence"].ok


def test_shared_premise_is_not_divergence():
    log = _good_log()
    for d in log["stages"]["divergence"]["directions"]:
        d["premise"] = "price as an itemized receipt"
    results = {r.stage: r for r in validate_process_log(log)}
    assert not results["divergence"].ok


def test_convergence_without_kills_fails():
    log = _good_log()
    log["stages"]["convergence"]["killed"] = []
    results = {r.stage: r for r in validate_process_log(log)}
    assert not results["convergence"].ok


def test_invention_without_reason_fails():
    log = _good_log()
    log["stages"]["build"]["invention_reasons"] = {}
    results = {r.stage: r for r in validate_process_log(log)}
    assert not results["build"].ok


def test_unwaived_block_failures_fail_self_lint():
    log = _good_log()
    log["stages"]["self_lint"]["unwaived_block_failures"] = 2
    results = {r.stage: r for r in validate_process_log(log)}
    assert not results["self_lint"].ok


def test_audit_only_subset():
    log = {"stages": {
        "self_lint": {"snapshot": "s.json", "unwaived_block_failures": 0},
        "critique": {"lenses_run": ["structure", "craft"], "verdicts": "v.json", "fails_addressed": True},
    }}
    results = validate_process_log(log, required_stages=("self_lint", "critique"))
    assert all(r.ok for r in results)


def test_unknown_stage_requested_raises():
    with pytest.raises(ProcessError):
        validate_process_log(_good_log(), required_stages=("vibes",))
