"""Apply committed pyproject.toml patches to sibling repos that lack them.

Some sibling repos (ux-qa-harness, visual-factory-kit, approval-inbox,
cmo-daily-dashboard) don't ship packaging metadata, so `pip install -e`
against them fails. The patches in sibling-patches/<repo-name>/pyproject.toml
are the committed, reproducible fix: this script copies each patch into the
sibling's working directory only if that sibling doesn't already have its
own pyproject.toml, so an existing/custom file is never overwritten.
"""
import shutil
from pathlib import Path


def apply_sibling_patches(dev_root: Path, patches_dir: Path) -> list[str]:
    """Copy patch pyproject.toml files into siblings that are missing one.

    For each subdirectory under patches_dir, if
    <dev_root>/<repo-name>/pyproject.toml does not already exist, copy the
    patch file into place. Returns the list of repo names that were patched.
    """
    patched = []
    for patch_repo_dir in sorted(p for p in patches_dir.iterdir() if p.is_dir()):
        repo_name = patch_repo_dir.name
        patch_file = patch_repo_dir / "pyproject.toml"
        if not patch_file.exists():
            continue
        target_pyproject = dev_root / repo_name / "pyproject.toml"
        if target_pyproject.exists():
            continue
        target_pyproject.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(patch_file, target_pyproject)
        patched.append(repo_name)
    return patched


if __name__ == "__main__":
    dev_root = Path("C:/Users/cgall/Desktop/dev")
    patches_dir = Path(__file__).parent.parent / "sibling-patches"
    patched = apply_sibling_patches(dev_root, patches_dir)
    if patched:
        print(f"Patched pyproject.toml for: {', '.join(patched)}")
    else:
        print("All siblings already had their own pyproject.toml; nothing patched.")
