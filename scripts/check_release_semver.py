"""Bloqueia promoção de código para main sem release SemVer no VERSION/CHANGELOG."""
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def version_tuple(value: str) -> tuple[int, int, int]:
    match = SEMVER.fullmatch(value.strip())
    if not match:
        raise ValueError(f"Versão SemVer inválida: {value!r}")
    return tuple(map(int, match.groups()))


def is_valid_step(old: str, new: str) -> bool:
    old_m, old_n, old_p = version_tuple(old)
    new_m, new_n, new_p = version_tuple(new)
    return (
        (new_m == old_m + 1 and new_n == 0 and new_p == 0)
        or (new_m == old_m and new_n == old_n + 1 and new_p == 0)
        or (new_m == old_m and new_n == old_n and new_p == old_p + 1)
    )


def is_material_change(path: str) -> bool:
    # Documentação isolada não exige bump; scripts, workflows e app exigem.
    if path in {"VERSION", "CHANGELOG.md", "AGENTS.md", "README.md"}:
        return False
    if path.startswith("docs/") or path.endswith(".md"):
        return False
    return True


def validate_release(old: str, new: str, files: list[str], changelog: str) -> None:
    version_tuple(old)
    version_tuple(new)
    material = any(is_material_change(p) for p in files)
    if old == new:
        if material:
            raise ValueError("PR para main altera código/configuração/CI sem bump em VERSION")
        return
    if not is_valid_step(old, new):
        raise ValueError("Bump SemVer deve ser exatamente MAJOR, MINOR ou PATCH sem salto arbitrário")
    release_header = re.compile(
        r"^## \[" + re.escape(new) + r"\] - \d{4}-\d{2}-\d{2}\s*$", re.MULTILINE
    )
    if not release_header.search(changelog):
        raise ValueError(f"CHANGELOG.md precisa de seção datada ## [{new}]")
    if "## [Não lançado]" not in changelog:
        raise ValueError("CHANGELOG.md precisa manter [Não lançado]")


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref", required=True)
    args = parser.parse_args()
    old = git("show", f"{args.base_ref}:VERSION")
    current = Path("VERSION").read_text(encoding="utf-8").strip()
    files = git("diff", "--name-only", args.base_ref, "HEAD").splitlines()
    changelog = Path("CHANGELOG.md").read_text(encoding="utf-8")
    validate_release(old, current, files, changelog)
    print(f"Release SemVer OK: {old} -> {current}; {len(files)} arquivos verificados")


if __name__ == "__main__":
    main()
