"""Refresh V7-derived brief and RSS; never rerun classification or rewrite old editions."""
from pathlib import Path
from xml.etree import ElementTree as ET
from canonical_publication import history_rows, canonical, validate
from generate_daily_brief import main as generate_brief
from maintenance_common import atomic_write_text


def feed(root):
    ns = "http://www.w3.org/2005/Atom"
    ET.register_namespace("", ns)
    tag = lambda s: "{" + ns + "}" + s
    doc = ET.Element(tag("feed"), {"{http://www.w3.org/XML/1998/namespace}lang": "es"})
    for name, text in (("id", "https://estrechoormuz.com/feed.xml"),
                       ("title", "Alertas V7 · Estrecho Ormuz"),
                       ("subtitle", "Cambios de evaluación del monitor; no observaciones AIS."),
                       ("updated", canonical(root)["generated_at"])):
        ET.SubElement(doc, tag(name)).text = text
    ET.SubElement(doc, tag("link"), href="https://estrechoormuz.com/feed.xml", rel="self")
    ET.SubElement(doc, tag("link"), href="https://estrechoormuz.com/historial.html")
    for row in history_rows(root)[:50]:
        entry = ET.SubElement(doc, tag("entry"))
        for name, text in (("id", "https://estrechoormuz.com/historial.html#" + row["id"]),
                           ("title", str(row.get("label_es") or row["state"]) + " · " + str(row.get("confidence") or "")),
                           ("updated", row["at"]), ("summary", row.get("summary_es", ""))):
            ET.SubElement(entry, tag(name)).text = str(text or "")
        ET.SubElement(entry, tag("link"), href="https://estrechoormuz.com/historial.html#" + row["id"])
    return ET.tostring(doc, encoding="unicode", xml_declaration=True) + "\n"


def main():
    root = Path(__file__).resolve().parent
    generate_brief()
    errors = validate(root)
    if errors:
        raise ValueError("; ".join(errors))
    atomic_write_text(root / "feed.xml", feed(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
