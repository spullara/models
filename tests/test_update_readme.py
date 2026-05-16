import importlib.util
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "update_readme.py"


spec = importlib.util.spec_from_file_location("update_readme", SCRIPT_PATH)
update_readme = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update_readme)


class UpdateReadmeTest(unittest.TestCase):
    def test_get_updates_for_date_range_includes_added_and_deleted_models(self):
        all_provider_data = {
            "OpenAI": {
                "current": {"old-model", "new-model", "newer-model"},
                "added": {
                    "old-model": "2026-05-09",
                    "new-model": "2026-05-10",
                    "newer-model": "2026-05-16",
                    "removed-same-day": "2026-05-16",
                },
                "deleted": {
                    "removed-model": "2026-05-16",
                    "older-removed-model": "2026-05-09",
                },
            },
            "Anthropic": {
                "current": {"claude"},
                "added": {"claude": "2026-05-09"},
                "deleted": {"older-claude": "2026-05-09"},
            },
        }

        updates = update_readme.get_updates_for_date_range(
            all_provider_data,
            "2026-05-10",
            "2026-05-16"
        )

        self.assertEqual(updates, {
            "OpenAI": {
                "added": [("newer-model", "2026-05-16"), ("new-model", "2026-05-10")],
                "deleted": [("removed-model", "2026-05-16")],
            }
        })

    def test_format_updates_section_lists_providers_in_readme_order(self):
        updates = {
            "Anthropic": {
                "added": [("claude-new", "2026-05-15")],
                "deleted": [],
            },
            "OpenAI": {
                "added": [("gpt-new", "2026-05-16")],
                "deleted": [("gpt-old", "2026-05-14")],
            },
        }

        section = update_readme.format_updates_section(
            updates,
            "2026-05-10",
            "2026-05-16"
        )

        self.assertLess(section.index("### OpenAI"), section.index("### Anthropic"))
        self.assertIn("## Updates This Week (2026-05-10 to 2026-05-16)", section)
        self.assertIn("- gpt-new (added: 2026-05-16)", section)
        self.assertIn("- gpt-old (deleted: 2026-05-14)", section)
        self.assertIn("- claude-new (added: 2026-05-15)", section)

    def test_format_updates_section_handles_no_updates(self):
        section = update_readme.format_updates_section({}, "2026-05-10", "2026-05-16")

        self.assertEqual(
            section,
            "## Updates This Week (2026-05-10 to 2026-05-16)\n\n"
            "No model changes detected this week.\n\n"
        )


if __name__ == "__main__":
    unittest.main()