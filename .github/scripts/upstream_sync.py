"""Merge hhursev/recipe-scrapers into this fork without dropping Souschef changes.

The merge is always a merge commit. Fork-only paths keep the fork version.
``recipe_scrapers/__init__.py`` imports and ``SCRAPERS`` entries are unioned.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


UPSTREAM_URL = "https://github.com/hhursev/recipe-scrapers.git"
IMPORTS_MARKER = "# === upstream-sync:scraper-imports ==="
SCRAPERS_MARKER = "# === upstream-sync:scrapers ==="
INIT_PATH = "recipe_scrapers/__init__.py"
MERGE_MESSAGE = "Merge upstream recipe-scrapers into souschef fork"

PRESERVATION = (
    (
        "group_ingredients_jp",
        "recipe_scrapers/_grouping_utils.py",
        "def group_ingredients_jp",
    ),
    (
        "site_recipe_fallback",
        "recipe_scrapers/_site_recipe_fallback.py",
        "class SiteRecipeFallbackScraper",
    ),
    (
        "targeted_tests",
        "tests/library/test_souschef_targeted_scrapers.py",
        "TARGETED_DOMAINS",
    ),
    ("utils_jp", "recipe_scrapers/_utils_jp.py", "def get_minutes_jp"),
    ("browser_headers", "recipe_scrapers/_abstract.py", "Mozilla/5.0"),
    ("cookpad", INIT_PATH, "CookPad.host()"),
    ("kurashiru", INIT_PATH, "Kurashiru.host()"),
    ("delishkitchen", INIT_PATH, "DelishKitchen.host()"),
    ("rakuten", INIT_PATH, "RakutenRecipe.host()"),
    ("nadia", INIT_PATH, "Nadia.host()"),
    ("macaroni", INIT_PATH, "Macaroni.host()"),
    ("lettuceclub", INIT_PATH, "LettuceClub.host()"),
    ("kikkoman_jp", INIT_PATH, "KikkomanJP.host()"),
    ("dancyu", INIT_PATH, "Dancyu.host()"),
    ("scrape_html", INIT_PATH, "def scrape_html"),
)


class GitError(RuntimeError):
    """A git command failed."""


@dataclass(frozen=True)
class ScraperImport:
    module: str
    names: tuple[str, ...]


@dataclass(frozen=True)
class ScraperEntry:
    key_src: str
    value_src: str


def git(
    repo: Path,
    args: list[str],
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("GIT_AUTHOR_NAME", "github-actions[bot]")
    env.setdefault(
        "GIT_AUTHOR_EMAIL",
        "41898282+github-actions[bot]@users.noreply.github.com",
    )
    env.setdefault("GIT_COMMITTER_NAME", env["GIT_AUTHOR_NAME"])
    env.setdefault("GIT_COMMITTER_EMAIL", env["GIT_AUTHOR_EMAIL"])
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise GitError(detail or f"git {' '.join(args)} failed")
    return result


def rev(repo: Path, ref: str) -> str:
    return git(repo, ["rev-parse", ref]).stdout.strip()


def ref_exists(repo: Path, ref: str) -> bool:
    result = git(repo, ["rev-parse", "--verify", "--quiet", ref], check=False)
    return result.returncode == 0


def is_ancestor(repo: Path, ancestor: str, descendant: str) -> bool:
    result = git(
        repo,
        ["merge-base", "--is-ancestor", ancestor, descendant],
        check=False,
    )
    return result.returncode == 0


def merge_in_progress(repo: Path) -> bool:
    result = git(repo, ["rev-parse", "-q", "--verify", "MERGE_HEAD"], check=False)
    return result.returncode == 0


def file_at(repo: Path, revision: str, path: str) -> str | None:
    result = git(repo, ["--no-pager", "show", f"{revision}:{path}"], check=False)
    if result.returncode != 0:
        return None
    return result.stdout


def load_manifest(path: Path) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {"fork_only": [], "dual_owned": []}
    current: str | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if not line.startswith(" ") and line.endswith(":"):
            current = line[:-1].strip()
            sections.setdefault(current, [])
            continue
        item = line.strip()
        if current and item.startswith("- "):
            sections[current].append(item[2:].strip().strip("'\""))
    return sections


def format_alias(alias: ast.alias) -> str:
    if alias.asname:
        return f"{alias.name} as {alias.asname}"
    return alias.name


def bound_name(alias: str) -> str:
    if " as " in alias:
        return alias.split(" as ", 1)[1].strip()
    return alias.strip()


def is_scraper_import(node: ast.stmt) -> bool:
    if not isinstance(node, ast.ImportFrom):
        return False
    if node.level != 1 or not node.module:
        return False
    return not node.module.startswith("_")


def is_scrapers_assign(node: ast.stmt) -> bool:
    if not isinstance(node, ast.Assign):
        return False
    return any(
        isinstance(target, ast.Name) and target.id == "SCRAPERS"
        for target in node.targets
    )


def extract_entries(source: str, node: ast.Assign) -> list[ScraperEntry]:
    if not isinstance(node.value, ast.Dict):
        raise ValueError("SCRAPERS is not a dict literal")
    entries: list[ScraperEntry] = []
    for key, value in zip(node.value.keys, node.value.values):
        if key is None or value is None:
            raise ValueError("SCRAPERS dict unpacking is not supported")
        key_src = ast.get_source_segment(source, key)
        value_src = ast.get_source_segment(source, value)
        if not key_src or not value_src:
            raise ValueError("Could not read a SCRAPERS entry")
        entries.append(ScraperEntry(key_src.strip(), value_src.strip()))
    return entries


def skeletonize(
    source: str,
) -> tuple[str, list[ScraperImport], list[ScraperEntry]]:
    tree = ast.parse(source)
    imports: list[ScraperImport] = []
    entries: list[ScraperEntry] = []
    import_spans: list[tuple[int, int]] = []
    scrapers_span: tuple[int, int] | None = None
    for node in tree.body:
        if is_scraper_import(node) and isinstance(node, ast.ImportFrom) and node.module:
            names = tuple(format_alias(alias) for alias in node.names)
            imports.append(ScraperImport(node.module, names))
            import_spans.append((node.lineno, node.end_lineno or node.lineno))
        elif is_scrapers_assign(node) and isinstance(node, ast.Assign):
            entries.extend(extract_entries(source, node))
            scrapers_span = (node.lineno, node.end_lineno or node.lineno)
    if not import_spans or scrapers_span is None:
        raise ValueError(f"{INIT_PATH} is missing scraper imports or SCRAPERS")

    lines = source.splitlines(keepends=True)
    first_import = min(start for start, _end in import_spans)
    last_import = max(end for _start, end in import_spans)
    skip: set[int] = set()
    for start, end in import_spans:
        skip.update(range(start, end + 1))
    for line_no in range(first_import, last_import + 1):
        if lines[line_no - 1].strip() == "":
            skip.add(line_no)
    scrapers_start, scrapers_end = scrapers_span
    skip.update(range(scrapers_start, scrapers_end + 1))

    output: list[str] = []
    inserted_imports = False
    inserted_scrapers = False
    for line_no, line in enumerate(lines, start=1):
        if not inserted_imports and line_no == first_import:
            output.append(IMPORTS_MARKER + "\n")
            inserted_imports = True
        if not inserted_scrapers and line_no == scrapers_start:
            output.append(SCRAPERS_MARKER + "\n")
            inserted_scrapers = True
        if line_no not in skip:
            output.append(line)
    return "".join(output), imports, entries


def union_imports(
    ours: list[ScraperImport],
    theirs: list[ScraperImport],
) -> list[ScraperImport]:
    order: list[str] = []
    names: dict[str, list[str]] = {}

    def add(item: ScraperImport) -> None:
        bucket = names.get(item.module)
        if bucket is None:
            order.append(item.module)
            bucket = []
            names[item.module] = bucket
        for name in item.names:
            if name not in bucket:
                bucket.append(name)

    for item in ours:
        add(item)
    for item in theirs:
        add(item)
    return [ScraperImport(module, tuple(names[module])) for module in order]


def normalize_src(src: str) -> str:
    return " ".join(src.split())


def default_host_class(key_src: str) -> str | None:
    try:
        expression = ast.parse(key_src, mode="eval").body
    except SyntaxError:
        return None
    if not isinstance(expression, ast.Call) or expression.args or expression.keywords:
        return None
    func = expression.func
    if not isinstance(func, ast.Attribute) or func.attr != "host":
        return None
    if not isinstance(func.value, ast.Name):
        return None
    return func.value.id


def union_entries(
    ours: list[ScraperEntry],
    theirs: list[ScraperEntry],
    resolve_host,
) -> tuple[list[ScraperEntry], list[str]]:
    notes: list[str] = []
    result: list[ScraperEntry] = []
    seen_keys: dict[str, ScraperEntry] = {}
    seen_hosts: dict[str, str] = {}

    def note(message: str) -> None:
        if message not in notes:
            notes.append(message)

    def add(entry: ScraperEntry, side: str) -> None:
        key = normalize_src(entry.key_src)
        existing = seen_keys.get(key)
        if existing is not None:
            if side == "theirs" and normalize_src(existing.value_src) != normalize_src(
                entry.value_src
            ):
                note(
                    "Kept fork SCRAPERS value "
                    f"{existing.value_src} for `{entry.key_src}`; "
                    f"upstream had {entry.value_src}."
                )
            return
        host = None
        class_name = default_host_class(entry.key_src)
        if class_name is not None and resolve_host is not None:
            host = resolve_host(class_name)
        if host and host in seen_hosts:
            note(f"Kept {seen_hosts[host]} for host {host}; dropped {entry.value_src}.")
            return
        seen_keys[key] = entry
        if host:
            seen_hosts[host] = entry.value_src
        result.append(entry)

    for entry in ours:
        add(entry, "ours")
    for entry in theirs:
        add(entry, "theirs")
    return result, notes


def prune_imports(
    imports: list[ScraperImport],
    entries: list[ScraperEntry],
    skeleton: str,
) -> list[ScraperImport]:
    used = {entry.value_src.strip() for entry in entries}
    pruned: list[ScraperImport] = []
    for item in imports:
        kept = []
        for name in item.names:
            bound = bound_name(name)
            if bound in used or bound in skeleton:
                kept.append(name)
        if kept:
            pruned.append(ScraperImport(item.module, tuple(kept)))
    return pruned


def render_imports(imports: list[ScraperImport]) -> str:
    lines: list[str] = []
    for item in imports:
        if len(item.names) == 1:
            lines.append(f"from .{item.module} import {item.names[0]}")
            continue
        body = ",\n    ".join(item.names)
        lines.append(f"from .{item.module} import (\n    {body},\n)")
    return "\n".join(lines)


def render_scrapers(entries: list[ScraperEntry]) -> str:
    lines = ["SCRAPERS = {"]
    for entry in entries:
        lines.append(f"    {entry.key_src}: {entry.value_src},")
    lines.append("}")
    return "\n".join(lines)


def splice(
    skeleton: str, imports: list[ScraperImport], entries: list[ScraperEntry]
) -> str:
    if skeleton.count(IMPORTS_MARKER) != 1 or skeleton.count(SCRAPERS_MARKER) != 1:
        raise ValueError(f"{INIT_PATH} skeleton did not keep exactly one union marker")
    return skeleton.replace(IMPORTS_MARKER, render_imports(imports), 1).replace(
        SCRAPERS_MARKER, render_scrapers(entries), 1
    )


def merge_skeletons(ours: str, base: str, theirs: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        ours_path = root / "ours"
        base_path = root / "base"
        theirs_path = root / "theirs"
        ours_path.write_text(ours, encoding="utf-8")
        base_path.write_text(base, encoding="utf-8")
        theirs_path.write_text(theirs, encoding="utf-8")
        result = subprocess.run(
            [
                "git",
                "merge-file",
                "-q",
                str(ours_path),
                str(base_path),
                str(theirs_path),
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode < 0:
            raise GitError(result.stderr.strip() or "git merge-file failed")
        return ours_path.read_text(encoding="utf-8")


def static_host(source: str, class_name: str) -> str | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        for item in node.body:
            if not isinstance(item, ast.FunctionDef) or item.name != "host":
                continue
            for statement in item.body:
                if not isinstance(statement, ast.Return):
                    continue
                value = statement.value
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    return value.value
    return None


def static_host_from_file(path: Path, class_name: str) -> str | None:
    if not path.is_file():
        return None
    try:
        return static_host(path.read_text(encoding="utf-8"), class_name)
    except (OSError, UnicodeError):
        return None


def make_resolver(repo: Path, imports: list[ScraperImport]):
    modules = {bound_name(name): item.module for item in imports for name in item.names}

    def resolve(class_name: str) -> str | None:
        module_name = modules.get(class_name)
        if not module_name:
            return None
        return static_host_from_file(
            repo / "recipe_scrapers" / f"{module_name}.py", class_name
        )

    return resolve


def empty_skeleton() -> str:
    return f"{IMPORTS_MARKER}\n\n{SCRAPERS_MARKER}\n"


def rebuild_init(
    ours_src: str,
    theirs_src: str,
    base_src: str,
    repo: Path,
    *,
    resolve_hosts: bool,
) -> tuple[str, list[str]]:
    ours_skeleton, ours_imports, ours_entries = skeletonize(ours_src)
    theirs_skeleton, theirs_imports, theirs_entries = skeletonize(theirs_src)
    if base_src.strip():
        base_skeleton, _, _ = skeletonize(base_src)
    else:
        base_skeleton = empty_skeleton()
    skeleton = merge_skeletons(ours_skeleton, base_skeleton, theirs_skeleton)
    imports = union_imports(ours_imports, theirs_imports)
    resolve_host = make_resolver(repo, imports) if resolve_hosts else None
    entries, notes = union_entries(ours_entries, theirs_entries, resolve_host)
    imports = prune_imports(imports, entries, skeleton)
    merged = splice(skeleton, imports, entries)
    ast.parse(merged)
    return merged, notes


def exists_in_commit(repo: Path, revision: str, path: str) -> bool:
    result = git(repo, ["cat-file", "-e", f"{revision}:{path}"], check=False)
    return result.returncode == 0


def changed_between(repo: Path, base: str, upstream_ref: str, path: str) -> bool:
    result = git(
        repo,
        ["diff", "--name-only", base, upstream_ref, "--", path],
        check=False,
    )
    if result.returncode != 0:
        return False
    return bool(result.stdout.strip())


def restore_fork_paths(
    repo: Path,
    fork_only: list[str],
    base: str,
    upstream_ref: str,
) -> list[str]:
    restored: list[str] = []
    for path in fork_only:
        if not changed_between(repo, base, upstream_ref, path):
            continue
        if not exists_in_commit(repo, "HEAD", path):
            continue
        git(repo, ["checkout", "HEAD", "--", path])
        restored.append(path)
    return restored


def files_with_markers(repo: Path) -> list[str]:
    result = git(
        repo,
        ["--no-pager", "grep", "-l", "-I", "-E", r"^<<<<<<< ", "--", "."],
        check=False,
    )
    if result.returncode > 1:
        raise GitError(result.stderr.strip() or "git grep failed")
    return [line for line in result.stdout.splitlines() if line]


def begin_merge(repo: Path, upstream_ref: str) -> bool:
    if is_ancestor(repo, upstream_ref, "HEAD"):
        return False
    result = git(repo, ["merge", "--no-ff", "--no-commit", upstream_ref], check=False)
    if merge_in_progress(repo):
        return True
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise GitError(detail or "git merge failed")
    return False


def resolve_init(repo: Path, *, resolve_hosts: bool) -> list[str]:
    ours = file_at(repo, "HEAD", INIT_PATH)
    theirs = file_at(repo, "MERGE_HEAD", INIT_PATH)
    if ours is None or theirs is None:
        return [f"{INIT_PATH} is missing on one side of the merge."]
    base_sha = git(repo, ["merge-base", "HEAD", "MERGE_HEAD"]).stdout.strip()
    base = file_at(repo, base_sha, INIT_PATH) or ""
    merged, notes = rebuild_init(
        ours,
        theirs,
        base,
        repo,
        resolve_hosts=resolve_hosts,
    )
    (repo / INIT_PATH).write_text(merged, encoding="utf-8")
    git(repo, ["add", "--", INIT_PATH])
    return notes


def merge_and_resolve(
    repo: Path,
    upstream_ref: str,
    fork_only: list[str],
    *,
    resolve_hosts: bool = True,
) -> dict[str, object]:
    if not begin_merge(repo, upstream_ref):
        return {
            "already_up_to_date": True,
            "kept_ours": [],
            "init_notes": [],
            "unresolved_conflicts": [],
            "parse_failed": False,
        }
    base = git(repo, ["merge-base", "HEAD", "MERGE_HEAD"]).stdout.strip()
    kept_ours = restore_fork_paths(repo, fork_only, base, "MERGE_HEAD")
    notes: list[str] = []
    parse_failed = False
    try:
        notes.extend(resolve_init(repo, resolve_hosts=resolve_hosts))
    except (ValueError, SyntaxError, GitError, OSError) as exc:
        parse_failed = True
        notes.append(f"Could not union {INIT_PATH} ({exc}).")
    git(repo, ["add", "-A"])
    return {
        "already_up_to_date": False,
        "kept_ours": kept_ours,
        "init_notes": notes,
        "unresolved_conflicts": files_with_markers(repo),
        "parse_failed": parse_failed,
    }


def preservation_report(repo: Path) -> dict[str, bool]:
    results: dict[str, bool] = {}
    for name, path, snippet in PRESERVATION:
        file_path = repo / path
        if not file_path.is_file():
            results[name] = False
            continue
        results[name] = snippet in file_path.read_text(encoding="utf-8")
    return results


def statement_source(source: str, node: ast.AST) -> str:
    start = getattr(node, "lineno", 1)
    decorators = getattr(node, "decorator_list", [])
    if decorators:
        start = min([start, *(decorator.lineno for decorator in decorators)])
    end = getattr(node, "end_lineno", start) or start
    return "\n".join(source.splitlines()[start - 1 : end])


def find_statement_source(source: str, name: str, kind: type) -> str | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    for node in tree.body:
        if isinstance(node, kind) and getattr(node, "name", None) == name:
            return statement_source(source, node)
    return None


def contract_changes(repo: Path, fork_ref: str, head_ref: str) -> list[str]:
    changed: list[str] = []
    for path in ("recipe_scrapers/_exceptions.py", "recipe_scrapers/_abstract.py"):
        result = git(
            repo, ["diff", "--quiet", fork_ref, head_ref, "--", path], check=False
        )
        if result.returncode != 0:
            changed.append(path)
    old_init = file_at(repo, fork_ref, INIT_PATH) or ""
    new_init = file_at(repo, head_ref, INIT_PATH) or ""
    old_scrape = find_statement_source(old_init, "scrape_html", ast.FunctionDef)
    new_scrape = find_statement_source(new_init, "scrape_html", ast.FunctionDef)
    if old_scrape != new_scrape:
        changed.append(f"{INIT_PATH}:scrape_html")
    old_groups = file_at(repo, fork_ref, "recipe_scrapers/_grouping_utils.py") or ""
    new_groups = file_at(repo, head_ref, "recipe_scrapers/_grouping_utils.py") or ""
    old_group = find_statement_source(old_groups, "IngredientGroup", ast.ClassDef)
    new_group = find_statement_source(new_groups, "IngredientGroup", ast.ClassDef)
    if old_group != new_group:
        changed.append("recipe_scrapers/_grouping_utils.py:IngredientGroup")
    return changed


def diff_names(repo: Path, base: str, head: str, paths: list[str]) -> list[str]:
    if not paths:
        return []
    result = git(repo, ["diff", "--name-only", base, head, "--", *paths])
    return [line for line in result.stdout.splitlines() if line]


def recommend_verdict(block_reasons: list[str], review_reasons: list[str]) -> str:
    if block_reasons:
        return "BLOCK"
    if review_reasons:
        return "REVIEW"
    return "SAFE"


def list_block_reasons(result: dict[str, object], preservation_ok: bool) -> list[str]:
    reasons: list[str] = []
    if result["unresolved_conflicts"]:
        reasons.append("unresolved conflict markers")
    if not preservation_ok:
        reasons.append("preservation checks failed")
    if result["parse_failed"]:
        reasons.append("__init__.py union failed")
    return reasons


def list_review_reasons(
    result: dict[str, object],
    contract: list[str],
    dual_owned: list[str],
) -> list[str]:
    reasons: list[str] = []
    if result["kept_ours"]:
        reasons.append("upstream changed fork-only paths")
    if result["init_notes"] and not result["parse_failed"]:
        reasons.append("SCRAPERS union kept the fork entry")
    if contract:
        reasons.append("Flask contract surface changed")
    if dual_owned:
        reasons.append("dual-owned files changed")
    return reasons


def as_str_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def as_bool_dict(value: object) -> dict[str, bool]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, bool] = {}
    for key, item in value.items():
        result[str(key)] = bool(item)
    return result


def format_bullet_list(items: list[str], empty: str = "none", limit: int = 30) -> str:
    if not items:
        return empty
    shown = items[:limit]
    lines = [f"- {item}" for item in shown]
    extra = len(items) - len(shown)
    if extra:
        lines.append(f"- ... and {extra} more")
    return "\n".join(lines)


def is_site_scraper(path: str) -> bool:
    name = Path(path).name
    return (
        path.startswith("recipe_scrapers/")
        and path.count("/") == 1
        and name.endswith(".py")
        and not name.startswith("_")
        and name != "__init__.py"
    )


def diff_names_filtered(
    repo: Path,
    merge_base: str,
    upstream_sha: str,
    diff_filter: str,
) -> list[str]:
    result = git(
        repo,
        [
            "diff",
            "--name-only",
            f"--diff-filter={diff_filter}",
            merge_base,
            upstream_sha,
            "--",
            "recipe_scrapers",
        ],
    )
    return [line for line in result.stdout.splitlines() if is_site_scraper(line)]


def upstream_change_summary(
    repo: Path,
    merge_base: str,
    upstream_sha: str,
) -> dict[str, list[str]]:
    subjects_raw = git(
        repo,
        ["log", "--reverse", "--pretty=format:%s", f"{merge_base}..{upstream_sha}"],
    ).stdout
    return {
        "subjects": [line for line in subjects_raw.splitlines() if line.strip()],
        "added_scrapers": diff_names_filtered(repo, merge_base, upstream_sha, "A"),
        "removed_scrapers": diff_names_filtered(repo, merge_base, upstream_sha, "D"),
        "modified_scrapers": diff_names_filtered(repo, merge_base, upstream_sha, "M"),
    }


def render_upstream_changes(summary: dict[str, object]) -> str:
    changes = summary.get("upstream_changes")
    if not isinstance(changes, dict):
        return ""
    return "\n".join(
        [
            "## Upstream changes",
            "",
            f"{summary.get('upstream_commit_count')} commits on `hhursev/recipe-scrapers` "
            f"since `{summary.get('merge_base')}`.",
            "",
            "### New site scrapers",
            format_bullet_list(as_str_list(changes.get("added_scrapers"))),
            "",
            "### Removed site scrapers",
            format_bullet_list(as_str_list(changes.get("removed_scrapers"))),
            "",
            "### Updated site scrapers",
            format_bullet_list(as_str_list(changes.get("modified_scrapers")), limit=60),
            "",
            "### Commits",
            format_bullet_list(as_str_list(changes.get("subjects")), limit=80),
            "",
        ]
    )


def safe_to_merge_line(verdict: str) -> str:
    if verdict == "SAFE":
        return "yes"
    if verdict == "REVIEW":
        return "no, human review required before merge"
    return "no"


def render_report(summary: dict[str, object]) -> str:
    verdict = str(summary.get("minimum_verdict") or summary.get("recommended_verdict"))
    contract = as_str_list(summary.get("contract_surface_changed"))
    contract_text = "unchanged" if not contract else format_bullet_list(contract)
    preservation = as_bool_dict(summary.get("preservation"))
    failed = [name for name, ok in preservation.items() if not ok]
    preservation_text = "ok" if not failed else format_bullet_list(failed)
    return "\n".join(
        [
            "## Upstream sync report",
            "",
            f"**Verdict: {verdict}**",
            "",
            f"Safe to merge to `main`: {safe_to_merge_line(verdict)}",
            "",
            "Flask installs the commit pinned in `souschef-flask-server` `requirements.txt`.",
            "Merging this PR to `main` updates that pin and redeploys production Flask.",
            "",
            f"- Upstream: `{summary.get('upstream_sha')}` "
            f"({summary.get('upstream_commit_count')} commits since `{summary.get('merge_base')}`)",
            f"- Fork main: `{summary.get('fork_sha')}`",
            f"- Merge commit: `{summary.get('merge_sha')}`",
            "- Fork-only paths kept because upstream also changed them:",
            format_bullet_list(as_str_list(summary.get("kept_ours"))),
            "- SCRAPERS union notes:",
            format_bullet_list(as_str_list(summary.get("init_notes"))),
            "- Dual-owned files changed:",
            format_bullet_list(as_str_list(summary.get("dual_owned_changed"))),
            f"- Flask contract surface: {contract_text}",
            f"- Preservation checks: {preservation_text}",
            "- Unresolved conflict markers:",
            format_bullet_list(as_str_list(summary.get("unresolved_conflicts"))),
            f"- unittest: {summary.get('unittest_status')}",
            f"- pre-commit: {summary.get('precommit_status')}",
            "",
            render_upstream_changes(summary),
            "The Cursor agent may raise this verdict. It may clear a conflict-marker or unittest",
            "failure only after that problem is actually fixed and the unittest command passes.",
            "",
        ]
    )


def render_pr_body(summary: dict[str, object]) -> str:
    verdict = summary.get("minimum_verdict") or summary.get("recommended_verdict")
    return "\n".join(
        [
            "## Summary",
            "",
            "Weekly merge of `hhursev/recipe-scrapers` `main` into the Souschef fork.",
            "",
            f"- Verdict: **{verdict}**",
            f"- Fork `main`: `{summary.get('fork_sha')}`",
            f"- Upstream: `{summary.get('upstream_sha')}`",
            f"- Merge base: `{summary.get('merge_base')}`",
            "- Strategy: merge commit (`--no-ff`), never rebase. Fork-only paths keep the Souschef version.",
            "",
            "This PR does not auto-merge. Merging to `main` pins this commit and redeploys production Flask.",
            "",
            render_upstream_changes(summary).rstrip(),
            "",
            "## Deterministic resolution",
            "",
            "Fork-only paths restored:",
            format_bullet_list(as_str_list(summary.get("kept_ours"))),
            "",
            "SCRAPERS union notes:",
            format_bullet_list(as_str_list(summary.get("init_notes"))),
            "",
            "Unresolved conflict markers:",
            format_bullet_list(as_str_list(summary.get("unresolved_conflicts"))),
            "",
            "The latest `Upstream sync report` comment is the Flask safety verdict.",
            "",
            "## Test plan",
            "",
            "- [ ] Invariant, Flask contract, and targeted scraper tests",
            "- [ ] Upstream sync report verdict reviewed",
            "- [ ] Human merge",
            "",
        ]
    )


def apply_test_results(
    summary: dict[str, object],
    unittest_status: str,
    precommit_status: str,
) -> dict[str, object]:
    block_reasons = as_str_list(summary.get("block_reasons"))
    review_reasons = as_str_list(summary.get("review_reasons"))
    if unittest_status == "failure" and "unittest failed" not in block_reasons:
        block_reasons.append("unittest failed")
    if precommit_status == "failure" and "pre-commit failed" not in review_reasons:
        review_reasons.append("pre-commit failed")
    verdict = recommend_verdict(block_reasons, review_reasons)
    summary["unittest_status"] = unittest_status
    summary["precommit_status"] = precommit_status
    summary["block_reasons"] = block_reasons
    summary["review_reasons"] = review_reasons
    summary["minimum_verdict"] = verdict
    summary["recommended_verdict"] = verdict
    summary["report_markdown"] = render_report(summary)
    return summary


def normalize_status(value: str) -> str:
    if value in {"success", "failure"}:
        return value
    return "not-run"


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_github_output(changed: bool, summary_path: Path) -> None:
    output = os.environ.get("GITHUB_OUTPUT")
    if not output:
        return
    with open(output, "a", encoding="utf-8") as handle:
        handle.write(f"changed={'true' if changed else 'false'}\n")
        handle.write(f"summary={summary_path}\n")


def ensure_clean(repo: Path) -> None:
    status = git(repo, ["status", "--porcelain", "--untracked-files=no"])
    if status.stdout.strip():
        raise GitError(
            "Refusing to sync with uncommitted tracked changes. Commit or stash them first."
        )


def ensure_upstream(repo: Path, url: str) -> None:
    remotes = git(repo, ["remote"]).stdout.split()
    if "upstream" in remotes:
        git(repo, ["remote", "set-url", "upstream", url])
    else:
        git(repo, ["remote", "add", "upstream", url])
    git(repo, ["fetch", "upstream", "main"])
    if "origin" in remotes:
        git(repo, ["fetch", "origin", "main"])
        git(repo, ["fetch", "origin", "sync/upstream"], check=False)


def format_with_black(repo: Path) -> None:
    if shutil.which("black") is None:
        return
    init_path = repo / INIT_PATH
    if not init_path.is_file():
        return
    subprocess.run(
        ["black", "--target-version", "py39", str(init_path)],
        cwd=repo,
        check=False,
    )


def commit_merge(repo: Path) -> None:
    git(repo, ["add", "-A"])
    git(
        repo,
        [
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-m",
            MERGE_MESSAGE,
        ],
    )


def up_to_date_summary(
    repo: Path, fork_ref: str, upstream_ref: str
) -> dict[str, object]:
    fork_sha = rev(repo, fork_ref)
    upstream_sha = rev(repo, upstream_ref)
    merge_base = git(repo, ["merge-base", fork_ref, upstream_ref]).stdout.strip()
    return {
        "changed": False,
        "already_up_to_date": True,
        "branch": "sync/upstream",
        "fork_sha": fork_sha,
        "upstream_sha": upstream_sha,
        "merge_base": merge_base,
        "merge_sha": fork_sha,
        "upstream_commit_count": 0,
        "kept_ours": [],
        "init_notes": [],
        "unresolved_conflicts": [],
        "preservation": {},
        "preservation_ok": True,
        "contract_surface_changed": [],
        "dual_owned_changed": [],
        "block_reasons": [],
        "review_reasons": [],
        "recommended_verdict": "SAFE",
        "minimum_verdict": "SAFE",
        "unittest_status": "not-run",
        "precommit_status": "not-run",
    }


def sync_command(args: argparse.Namespace) -> int:
    repo = Path(args.repo_root).resolve()
    summary_path = Path(args.summary)
    manifest = load_manifest(repo / ".github/upstream-sync/ours-paths.yml")
    if not args.skip_fetch:
        ensure_upstream(repo, args.upstream_url)
    fork_ref = "origin/main" if ref_exists(repo, "origin/main") else "main"
    upstream_ref = "upstream/main"
    if not ref_exists(repo, upstream_ref):
        raise GitError(
            "upstream/main is not available. Fetch hhursev/recipe-scrapers first."
        )
    if not ref_exists(repo, fork_ref):
        raise GitError(f"{fork_ref} is not available.")

    fork_sha = rev(repo, fork_ref)
    upstream_sha = rev(repo, upstream_ref)
    merge_base = git(repo, ["merge-base", fork_ref, upstream_ref]).stdout.strip()
    if is_ancestor(repo, upstream_ref, fork_ref):
        summary = up_to_date_summary(repo, fork_ref, upstream_ref)
        write_json(summary_path, summary)
        write_github_output(False, summary_path)
        print(f"Already up to date with {upstream_ref} at {upstream_sha}.")
        return 0

    ensure_clean(repo)
    git(repo, ["checkout", "-B", args.branch, fork_ref])
    result = merge_and_resolve(
        repo,
        upstream_ref,
        manifest["fork_only"],
        resolve_hosts=not args.skip_host_resolution,
    )
    if result["already_up_to_date"]:
        summary = up_to_date_summary(repo, fork_ref, upstream_ref)
        write_json(summary_path, summary)
        write_github_output(False, summary_path)
        print(f"Already up to date with {upstream_ref} at {upstream_sha}.")
        return 0

    format_with_black(repo)
    commit_merge(repo)
    merge_sha = rev(repo, "HEAD")
    preservation = preservation_report(repo)
    preservation_ok = all(preservation.values())
    contract = contract_changes(repo, fork_ref, "HEAD")
    dual_paths = [path for path in manifest["dual_owned"] if path != INIT_PATH]
    dual_owned = diff_names(repo, fork_ref, "HEAD", dual_paths)
    block_reasons = list_block_reasons(result, preservation_ok)
    review_reasons = list_review_reasons(result, contract, dual_owned)
    verdict = recommend_verdict(block_reasons, review_reasons)
    commit_count = git(
        repo,
        ["rev-list", "--count", f"{merge_base}..{upstream_sha}"],
    ).stdout.strip()
    summary = {
        "changed": True,
        "already_up_to_date": False,
        "branch": args.branch,
        "fork_sha": fork_sha,
        "upstream_sha": upstream_sha,
        "merge_base": merge_base,
        "merge_sha": merge_sha,
        "upstream_commit_count": int(commit_count or "0"),
        "upstream_changes": upstream_change_summary(repo, merge_base, upstream_sha),
        "kept_ours": result["kept_ours"],
        "init_notes": result["init_notes"],
        "unresolved_conflicts": result["unresolved_conflicts"],
        "preservation": preservation,
        "preservation_ok": preservation_ok,
        "contract_surface_changed": contract,
        "dual_owned_changed": dual_owned,
        "block_reasons": block_reasons,
        "review_reasons": review_reasons,
        "recommended_verdict": verdict,
        "minimum_verdict": verdict,
        "unittest_status": "not-run",
        "precommit_status": "not-run",
    }
    summary["report_markdown"] = render_report(summary)
    write_json(summary_path, summary)
    if args.pr_body:
        Path(args.pr_body).write_text(render_pr_body(summary), encoding="utf-8")
    write_github_output(True, summary_path)
    print(
        f"Merged {upstream_sha} into {fork_sha} as {merge_sha} "
        f"with preliminary verdict {verdict}."
    )
    return 0


def render_report_command(args: argparse.Namespace) -> int:
    summary_path = Path(args.summary)
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary = apply_test_results(
        summary,
        normalize_status(args.unittest_status),
        normalize_status(args.precommit_status),
    )
    write_json(summary_path, summary)
    report = str(summary["report_markdown"])
    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
    if args.pr_body:
        body_path = Path(args.pr_body)
        body_path.parent.mkdir(parents=True, exist_ok=True)
        body_path.write_text(render_pr_body(summary), encoding="utf-8")
    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as handle:
            handle.write(report)
    print(report)
    return 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--summary", required=True)
    parser.add_argument("--pr-body", default="")
    parser.add_argument("--report", default="")
    parser.add_argument("--upstream-url", default=UPSTREAM_URL)
    parser.add_argument("--branch", default="sync/upstream")
    parser.add_argument("--skip-fetch", action="store_true")
    parser.add_argument("--skip-host-resolution", action="store_true")
    parser.add_argument("--render-report", action="store_true")
    parser.add_argument("--unittest-status", default="not-run")
    parser.add_argument("--precommit-status", default="not-run")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.render_report:
        return render_report_command(args)
    return sync_command(args)


if __name__ == "__main__":
    raise SystemExit(main())
