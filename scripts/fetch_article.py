"""Volltext der Primärpublikation über den Europe-PMC-Dienst sichern."""

import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

target = Path("research")
target.mkdir(exist_ok=True)
url = "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC10710515/fullTextXML"
content = urllib.request.urlopen(url, timeout=45).read()
root = ET.fromstring(content)
if not any(node.text == "10.1038/s41597-023-02808-6" for node in root.findall(".//article-id")):
    raise ValueError("Unerwartete Publikationskennung")
(target / "article.xml").write_bytes(content)
text = "\n".join(" ".join(section.itertext()) for section in root.findall(".//body/sec"))
(target / "article.txt").write_text(text, encoding="utf-8")
print("Geprüfter Artikelvolltext gespeichert.")
