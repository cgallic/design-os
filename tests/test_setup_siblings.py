from scripts.setup_siblings import apply_sibling_patches


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_apply_sibling_patches_copies_missing_and_leaves_existing_untouched(tmp_path):
    dev_root = tmp_path / "dev"
    patches_dir = tmp_path / "sibling-patches"

    # Sibling missing pyproject.toml: patch should be copied in.
    missing_sibling = dev_root / "missing-repo"
    missing_sibling.mkdir(parents=True)
    patch_content = "[project]\nname = \"missing-repo\"\n"
    _write(patches_dir / "missing-repo" / "pyproject.toml", patch_content)

    # Sibling that already has its own pyproject.toml: must be left alone.
    present_sibling = dev_root / "present-repo"
    present_sibling.mkdir(parents=True)
    existing_content = "[project]\nname = \"present-repo-original\"\n"
    _write(present_sibling / "pyproject.toml", existing_content)
    _write(
        patches_dir / "present-repo" / "pyproject.toml",
        "[project]\nname = \"present-repo-patch-should-not-apply\"\n",
    )
    before = (present_sibling / "pyproject.toml").read_text(encoding="utf-8")

    patched = apply_sibling_patches(dev_root, patches_dir)

    assert patched == ["missing-repo"]

    copied = (missing_sibling / "pyproject.toml").read_text(encoding="utf-8")
    assert copied == patch_content

    after = (present_sibling / "pyproject.toml").read_text(encoding="utf-8")
    assert after == before == existing_content
