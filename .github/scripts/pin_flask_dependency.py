"""Pin souschef-flask-server's recipe-scrapers install to one commit.

Flask production is built by Nixpacks from the Flask repository. The install
layer is reused while requirements.txt stays the same, so a branch URL such as
``@main`` can keep an older checkout after a redeploy. Replacing that line with
a full commit SHA changes the file Railway hashes and makes the next Flask
build install that commit.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

PIN_RE = re.compile(
    r"^git\+https://github\.com/arisa-s/recipe-scrapers\.git@"
    r"[A-Za-z0-9._-]+#egg=recipe_scrapers$",
    re.MULTILINE,
)
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def pinned_requirement(sha: str) -> str:
    if SHA_RE.fullmatch(sha) is None:
        raise ValueError("recipe-scrapers pin must be a 40-character commit SHA")
    return (
        "git+https://github.com/arisa-s/recipe-scrapers.git@"
        f"{sha}#egg=recipe_scrapers"
    )


def update_requirements(text: str, sha: str) -> str:
    replacement = pinned_requirement(sha)
    matches = PIN_RE.findall(text)
    if len(matches) != 1:
        raise ValueError(
            "requirements.txt must contain exactly one recipe-scrapers git pin"
        )
    return PIN_RE.sub(replacement, text, count=1)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "usage: pin_flask_dependency.py <requirements.txt> <sha>",
            file=sys.stderr,
        )
        return 2

    path = Path(argv[1])
    sha = argv[2].strip()
    try:
        updated = update_requirements(path.read_text(encoding="utf-8"), sha)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    path.write_text(updated, encoding="utf-8")
    print(f"pinned recipe-scrapers to {sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
