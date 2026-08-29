from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RADAR_URL = (
    "https://www.marinetraffic.com/en/ais/home/"
    "centerx:57.7/centery:25.8/zoom:6"
)


class RadarContractTests(unittest.TestCase):
    def test_homepages_use_native_external_radar_link(self):
        for name in ("index.html", "en.html"):
            body = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn('data-open-marine-radar', body, name)
            self.assertIn(f'href="{RADAR_URL}"', body, name)
            self.assertIn('target="_blank"', body, name)
            self.assertIn('rel="noopener noreferrer"', body, name)
            self.assertNotIn("data-load-marine-map", body, name)

    def test_blocked_embed_is_not_reintroduced(self):
        files = ("index.html", "en.html", "app.js", "build_public_site.py")
        for name in files:
            body = (ROOT / name).read_text(encoding="utf-8")
            self.assertNotIn("/ais/embed/", body, name)


if __name__ == "__main__":
    unittest.main()
