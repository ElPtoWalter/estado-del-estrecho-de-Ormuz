import tempfile
import unittest
from pathlib import Path

from adsense_prerender import remove_trailing_corruption, replace_content


class PrerenderIdempotenceTests(unittest.TestCase):
    def test_nested_container_is_replaced_without_leaving_old_cards(self):
        source = '<div id="briefEvidence"><article><div>old</div></article></div><p>after</p>'
        rendered = '<article><div>new</div></article>'
        first = replace_content(source, "briefEvidence", rendered)
        second = replace_content(first, "briefEvidence", rendered)
        self.assertEqual(first, second)
        self.assertNotIn("old", first)
        self.assertEqual(first.count("new"), 1)
        self.assertTrue(first.endswith("<p>after</p>"))

    def test_legacy_cards_after_container_are_removed(self):
        source = (
            '<section><div id="briefEvidence"><article><div>new</div></article></div>'
            '<article><div>legacy</div></article></section><section>next</section>'
        )
        cleaned = remove_trailing_corruption(source, "briefEvidence")
        self.assertNotIn("legacy", cleaned)
        self.assertIn("new", cleaned)
        self.assertTrue(cleaned.endswith("<section>next</section>"))


if __name__ == "__main__":
    unittest.main()
