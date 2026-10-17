import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / ".github" / "scripts" / "pin_flask_dependency.py"
WORKFLOW = ROOT / ".github" / "workflows" / "deploy-flask.yml"
SHA = "410e129349ab623afab43d2d712d3bdc5747bfd1"
OTHER_SHA = "aa2231a3eb3ee94aa3b08eadccfa0b72529bf822"


def load_pinner():
    spec = importlib.util.spec_from_file_location("pin_flask_dependency", SCRIPT)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Cannot load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


PINNER = load_pinner()


def requirement(revision: str) -> str:
    return (
        "git+https://github.com/arisa-s/recipe-scrapers.git@"
        f"{revision}#egg=recipe_scrapers"
    )


class TestPinFlaskDependency(unittest.TestCase):
    def test_replaces_branch_pin_with_commit(self):
        original = "\n".join(
            ["Flask==3.0.0", requirement("main"), "gunicorn==21.2.0", ""]
        )

        updated = PINNER.update_requirements(original, SHA)

        self.assertIn(requirement(SHA), updated)
        self.assertNotIn(requirement("main"), updated)
        self.assertTrue(updated.startswith("Flask==3.0.0\n"))
        self.assertTrue(updated.endswith("gunicorn==21.2.0\n"))

    def test_replaces_previous_commit_pin(self):
        updated = PINNER.update_requirements(requirement(OTHER_SHA) + "\n", SHA)

        self.assertEqual(updated, requirement(SHA) + "\n")

    def test_same_commit_keeps_the_file_text(self):
        original = requirement(SHA) + "\n"

        self.assertEqual(PINNER.update_requirements(original, SHA), original)

    def test_rejects_a_short_or_branch_revision(self):
        original = requirement("main") + "\n"

        for revision in ("main", SHA[:12], SHA.upper()):
            with self.subTest(revision=revision):
                with self.assertRaises(ValueError):
                    PINNER.update_requirements(original, revision)

    def test_requires_exactly_one_pin(self):
        with self.assertRaises(ValueError):
            PINNER.update_requirements("Flask==3.0.0\n", SHA)
        with self.assertRaises(ValueError):
            PINNER.update_requirements(
                requirement("main") + "\n" + requirement(SHA) + "\n", SHA
            )

    def test_cli_writes_the_pin(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "requirements.txt"
            path.write_text(requirement("main") + "\n", encoding="utf-8")

            with contextlib.redirect_stdout(io.StringIO()):
                status = PINNER.main(["pin_flask_dependency.py", str(path), SHA])

            self.assertEqual(status, 0)
            self.assertEqual(path.read_text(encoding="utf-8"), requirement(SHA) + "\n")

    def test_deploy_workflow_pushes_the_pin_to_flask_main(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("branches: [main]", workflow)
        self.assertIn("repository: arisa-s/souschef-flask-server", workflow)
        self.assertIn("ref: main", workflow)
        self.assertIn("ssh-key: ${{ secrets.FLASK_DEPLOY_KEY }}", workflow)
        self.assertIn("pin_flask_dependency.py", workflow)
        self.assertIn("git push origin HEAD:main", workflow)
