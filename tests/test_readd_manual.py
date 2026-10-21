import shutil
import unittest
from pathlib import Path

from tools.zed_i18n.readd_manual import (
    keys_dropped_by_extraction,
    readd_manual_strings,
    span_matches,
)


class ReaddManualTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path.cwd() / "tests" / ".tmp" / self._testMethodName
        shutil.rmtree(self.root, ignore_errors=True)
        (self.root / "crates" / "demo").mkdir(parents=True)
        self.source_text = 'const MESSAGE: &str = "Share is down. Save anyway?";\n'
        self.source = self.root / "crates" / "demo" / "message.rs"
        self.source.write_text(self.source_text, encoding="utf-8")
        self.key = "Share is down. Save anyway?"
        start = self.source_text.index(self.key)
        self.entry = {
            "occurrences": [
                {
                    "call": "prompt",
                    "end_byte": start + len(self.key),
                    "file": "crates/demo/message.rs",
                    "kind": "prompt_message",
                    "line": 1,
                    "start_byte": start,
                }
            ],
            "status": "accepted",
        }

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_readds_a_string_whose_span_still_matches(self) -> None:
        previous_manifest = {self.key: self.entry}
        current_manifest: dict[str, dict[str, object]] = {}
        current_catalog: dict[str, str] = {}

        readded, mismatched = readd_manual_strings(
            previous_manifest, {self.key: self.key}, current_manifest, current_catalog, self.root
        )

        self.assertEqual(readded, [self.key])
        self.assertEqual(mismatched, [])
        self.assertEqual(current_manifest[self.key], self.entry)
        self.assertEqual(current_catalog[self.key], self.key)

    def test_reports_a_string_whose_span_moved(self) -> None:
        first = self.entry["occurrences"][0]
        moved = {
            **first,
            "start_byte": first["start_byte"] + 1,
            "end_byte": first["end_byte"] + 1,
        }
        entry = {**self.entry, "occurrences": [moved]}

        readded, mismatched = readd_manual_strings(
            {self.key: entry},
            {self.key: self.key},
            {},
            {},
            self.root,
        )

        self.assertEqual(readded, [])
        self.assertEqual(mismatched, [self.key])

    def test_reports_a_string_whose_file_disappeared(self) -> None:
        shutil.rmtree(self.root / "crates")

        readded, mismatched = readd_manual_strings(
            {self.key: self.entry},
            {self.key: self.key},
            {},
            {},
            self.root,
        )

        self.assertEqual(readded, [])
        self.assertEqual(mismatched, [self.key])

    def test_only_lists_registered_strings_the_scanner_dropped(self) -> None:
        previous_manifest = {
            "kept by the scanner": {"occurrences": [], "status": "accepted"},
            self.key: self.entry,
            "needs review": {"occurrences": [], "status": "needs_review"},
        }
        current_manifest = {"kept by the scanner": {"occurrences": [], "status": "accepted"}}

        self.assertEqual(
            keys_dropped_by_extraction(previous_manifest, current_manifest),
            [self.key],
        )

    def test_span_matches_uses_the_checkout_relative_path(self) -> None:
        occurrence = self.entry["occurrences"][0]

        self.assertTrue(span_matches(self.root, self.key, occurrence))
        self.assertFalse(span_matches(self.root, "not in the file", occurrence))


if __name__ == "__main__":
    unittest.main()
