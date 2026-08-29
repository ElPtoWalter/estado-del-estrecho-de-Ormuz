from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RADAR_URL = (
    "https://www.marinetraffic.com/en/ais/home/"
    "centerx:56.3/centery:26.6/zoom:7"
)
WIDGET_SCRIPT = "https://www.myshiptracking.com/js/widgetApi.js"


class RadarContractTests(unittest.TestCase):
    def test_homepages_offer_on_demand_embedded_radar(self):
        for name in ("index.html", "en.html"):
            body = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn('data-load-ais-map', body, name)
            self.assertIn('id="marineMapContainer"', body, name)
            self.assertIn('id="marineMapPlaceholder"', body, name)
            self.assertIn('id="marineMapToolbar"', body, name)
            self.assertIn('defer src="/radar-map.js"', body, name)
            self.assertIn('data-open-marine-radar', body, name)
            self.assertIn(f'href="{RADAR_URL}"', body, name)
            self.assertIn('target="_blank"', body, name)
            self.assertIn('rel="noopener noreferrer"', body, name)

    def test_widget_is_configured_for_hormuz_and_loaded_on_demand(self):
        for name in ("radar-map.js",):
            body = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn(WIDGET_SCRIPT, body, name)
            self.assertIn('mst_lat', body, name)
            self.assertIn('26.55', body, name)
            self.assertIn('mst_lng', body, name)
            self.assertIn('56.32', body, name)
            self.assertIn('myshiptrackingscript', body, name)
            self.assertIn('traffic-map-frame', body, name)

    def test_blocked_embed_is_not_reintroduced(self):
        files = ("index.html", "en.html", "app.js", "build_public_site.py")
        for name in files:
            body = (ROOT / name).read_text(encoding="utf-8")
            self.assertNotIn("/ais/embed/", body, name)


if __name__ == "__main__":
    unittest.main()
