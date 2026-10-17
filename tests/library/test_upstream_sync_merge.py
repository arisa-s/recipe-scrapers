import ast
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / ".github" / "scripts" / "upstream_sync.py"


def load_sync():
    spec = importlib.util.spec_from_file_location("upstream_sync", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


SYNC = load_sync()


def run_git(repo, *args):
    env = os.environ.copy()
    env["GIT_AUTHOR_NAME"] = "Test"
    env["GIT_AUTHOR_EMAIL"] = "test@example.com"
    env["GIT_COMMITTER_NAME"] = "Test"
    env["GIT_COMMITTER_EMAIL"] = "test@example.com"
    subprocess.run(
        ["git", "-C", str(repo), "-c", "commit.gpgsign=false", *args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )


def write_file(repo, path, text):
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def commit_all(repo, message):
    run_git(repo, "add", "-A")
    run_git(repo, "commit", "-m", message)


def init_source(imports, scrapers, scrape_body):
    import_lines = "\n".join(
        f"from .{name} import {class_name}" for name, class_name in imports
    )
    scraper_lines = "\n".join(
        f"    {class_name}.host(): {class_name}," for class_name in scrapers
    )
    return (
        "from __future__ import annotations\n"
        "\n"
        f"{import_lines}\n"
        "\n"
        "SCRAPERS = {\n"
        f"{scraper_lines}\n"
        "}\n"
        "\n"
        "def scrape_html():\n"
        f"    return {scrape_body!r}\n"
    )


def host_module(class_name, host):
    return (
        f"class {class_name}:\n"
        "    @classmethod\n"
        "    def host(cls):\n"
        f"        return {host!r}\n"
    )


class TestUpstreamSyncMerge(unittest.TestCase):
    def test_manifest_paths_exist(self):
        manifest = SYNC.load_manifest(ROOT / ".github/upstream-sync/ours-paths.yml")
        for path in manifest["fork_only"] + manifest["dual_owned"]:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).exists(), path)

    def test_roundtrip_preserves_real_init_contract(self):
        source = (ROOT / "recipe_scrapers/__init__.py").read_text(encoding="utf-8")
        skeleton, imports, entries = SYNC.skeletonize(source)
        rebuilt = SYNC.splice(skeleton, imports, entries)
        _, rebuilt_imports, rebuilt_entries = SYNC.skeletonize(rebuilt)

        self.assertEqual(imports, rebuilt_imports)
        self.assertEqual(entries, rebuilt_entries)
        self.assertEqual(
            SYNC.find_statement_source(source, "scrape_html", ast.FunctionDef),
            SYNC.find_statement_source(rebuilt, "scrape_html", ast.FunctionDef),
        )
        self.assertNotIn("<<<<<<<", rebuilt)
        self.assertIn(SYNC.IMPORTS_MARKER, skeleton)
        self.assertNotIn(SYNC.IMPORTS_MARKER, rebuilt)

    def test_static_host_reads_simple_return(self):
        source = host_module("Kurashiru", "kurashiru.com")
        self.assertEqual(SYNC.static_host(source, "Kurashiru"), "kurashiru.com")
        self.assertIsNone(
            SYNC.static_host(
                "class Foo:\n    def host(cls, domain='x'):\n        return domain\n",
                "Foo",
            )
        )

    def test_union_drops_upstream_class_for_same_host(self):
        ours = [SYNC.ScraperEntry("Kurashiru.host()", "Kurashiru")]
        theirs = [
            SYNC.ScraperEntry("Kurashiru.host()", "Kurashiru"),
            SYNC.ScraperEntry("Other.host()", "Other"),
        ]
        hosts = {"Kurashiru": "kurashiru.com", "Other": "kurashiru.com"}
        entries, notes = SYNC.union_entries(ours, theirs, hosts.get)

        self.assertEqual([entry.value_src for entry in entries], ["Kurashiru"])
        self.assertTrue(any("kurashiru.com" in note for note in notes))

    def test_pr_body_summarizes_upstream_scrapers_and_commits(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            run_git(repo, "init", "-b", "main")
            write_file(repo, "recipe_scrapers/aaa.py", "class Aaa:\n    pass\n")
            commit_all(repo, "base")
            base = SYNC.rev(repo, "HEAD")
            run_git(repo, "checkout", "-b", "upstream-main")
            write_file(repo, "recipe_scrapers/bbb.py", "class Bbb:\n    pass\n")
            write_file(
                repo, "recipe_scrapers/aaa.py", "class Aaa:\n    changed = True\n"
            )
            commit_all(repo, "Add Bbb scraper")

            changes = SYNC.upstream_change_summary(repo, base, "upstream-main")
            body = SYNC.render_pr_body(
                {
                    "minimum_verdict": "REVIEW",
                    "fork_sha": "fork",
                    "upstream_sha": "upstream",
                    "merge_base": base,
                    "upstream_commit_count": 1,
                    "kept_ours": [],
                    "init_notes": [],
                    "unresolved_conflicts": [],
                    "upstream_changes": changes,
                }
            )

        self.assertIn("recipe_scrapers/bbb.py", changes["added_scrapers"])
        self.assertIn("recipe_scrapers/aaa.py", changes["modified_scrapers"])
        self.assertEqual(changes["subjects"], ["Add Bbb scraper"])
        self.assertIn("## Upstream changes", body)
        self.assertIn("### New site scrapers", body)
        self.assertIn("recipe_scrapers/bbb.py", body)
        self.assertIn("Add Bbb scraper", body)

    def test_unittest_failure_blocks_an_otherwise_safe_merge(self):
        summary = SYNC.apply_test_results(
            {
                "block_reasons": [],
                "review_reasons": [],
                "kept_ours": [],
                "init_notes": [],
                "unresolved_conflicts": [],
                "dual_owned_changed": [],
                "contract_surface_changed": [],
                "preservation": {},
                "upstream_sha": "a",
                "merge_base": "b",
                "fork_sha": "c",
                "merge_sha": "d",
                "upstream_commit_count": 1,
            },
            "failure",
            "success",
        )
        self.assertEqual(summary["minimum_verdict"], "BLOCK")
        self.assertIn("unittest failed", summary["block_reasons"])

    def test_merge_keeps_fork_files_and_unions_registrations(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            run_git(repo, "init", "-b", "main")
            write_file(
                repo,
                "recipe_scrapers/__init__.py",
                init_source(
                    [("aaa", "Aaa")],
                    ["Aaa"],
                    "base",
                ),
            )
            write_file(
                repo, "recipe_scrapers/aaa.py", host_module("Aaa", "aaa.example")
            )
            write_file(repo, "recipe_scrapers/_utils_jp.py", "VALUE = 'base'\n")
            write_file(repo, "recipe_scrapers/cookpad.py", "VERSION = 'base'\n")
            commit_all(repo, "base")

            run_git(repo, "checkout", "-b", "upstream-main")
            write_file(
                repo,
                "recipe_scrapers/__init__.py",
                init_source(
                    [("aaa", "Aaa"), ("bbb", "Bbb"), ("other", "Other")],
                    ["Aaa", "Bbb", "Other"],
                    "upstream",
                ),
            )
            write_file(
                repo, "recipe_scrapers/bbb.py", host_module("Bbb", "bbb.example")
            )
            write_file(
                repo, "recipe_scrapers/other.py", host_module("Other", "kurashiru.com")
            )
            write_file(repo, "recipe_scrapers/_utils_jp.py", "VALUE = 'upstream'\n")
            write_file(repo, "recipe_scrapers/cookpad.py", "VERSION = 'upstream'\n")
            commit_all(repo, "upstream")

            run_git(repo, "checkout", "main")
            write_file(
                repo,
                "recipe_scrapers/__init__.py",
                init_source(
                    [("aaa", "Aaa"), ("kurashiru", "Kurashiru")],
                    ["Aaa", "Kurashiru"],
                    "base",
                ),
            )
            write_file(
                repo,
                "recipe_scrapers/kurashiru.py",
                host_module("Kurashiru", "kurashiru.com"),
            )
            write_file(repo, "recipe_scrapers/_utils_jp.py", "VALUE = 'ours'\n")
            write_file(repo, "recipe_scrapers/cookpad.py", "VERSION = 'ours'\n")
            commit_all(repo, "fork")

            result = SYNC.merge_and_resolve(
                repo,
                "upstream-main",
                ["recipe_scrapers/_utils_jp.py"],
            )
            init_text = (repo / "recipe_scrapers/__init__.py").read_text(
                encoding="utf-8"
            )
            utils_text = (repo / "recipe_scrapers/_utils_jp.py").read_text(
                encoding="utf-8"
            )
            cookpad_text = (repo / "recipe_scrapers/cookpad.py").read_text(
                encoding="utf-8"
            )

            self.assertIn("Kurashiru.host()", init_text)
            self.assertIn("Bbb.host()", init_text)
            self.assertNotIn("Other.host()", init_text)
            self.assertIn("return 'upstream'", init_text)
            self.assertIn("VALUE = 'ours'", utils_text)
            self.assertNotIn("upstream", utils_text)
            self.assertIn("<<<<<<<", cookpad_text)
            with self.assertRaises(SYNC.GitError):
                SYNC.commit_merge(repo)
            SYNC.release_conflicted_merge(repo, "sync/upstream", "upstream-main")
            published = (repo / "recipe_scrapers/cookpad.py").read_text(
                encoding="utf-8"
            )
            self.assertNotIn("<<<<<<<", published)
            self.assertFalse(SYNC.merge_in_progress(repo))
            self.assertEqual(SYNC.rev(repo, "HEAD"), SYNC.rev(repo, "upstream-main"))
            self.assertIn("recipe_scrapers/_utils_jp.py", result["kept_ours"])
            self.assertIn("recipe_scrapers/cookpad.py", result["unresolved_conflicts"])
            self.assertNotIn(
                "recipe_scrapers/__init__.py", result["unresolved_conflicts"]
            )
            self.assertTrue(
                any("kurashiru.com" in note for note in result["init_notes"])
            )
