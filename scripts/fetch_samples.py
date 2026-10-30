import json
import urllib.parse
import urllib.request
from pathlib import Path

base = "https://lab.compute.dtu.dk/api/v4/projects/1804/repository/files/"
tree = json.loads(Path("research/gitlab_tree.json").read_text())
commit = json.loads(Path("research/gitlab_commit.json").read_text())["id"]
selected = [
    x["path"]
    for x in tree
    if x["type"] == "blob"
    and (
        "service_reports/Revco/806031/service_02_03_2023/" in x["path"]
        or "service_reports/Revco/806030/service_30_08_2022/" in x["path"]
        or "service_reports/Revco/808783/service_14_09_2021/" in x["path"]
    )
]
selected += [
    next(
        x["path"]
        for x in tree
        if x["type"] == "blob"
        and x["path"].startswith("data/raw_data/Revco/806018/temp/")
        and "202210" in x["path"]
    ),
    "data/raw_data/Haier/809169/lowtemperbox.db",
]
for p in selected:
    target = Path("research/samples") / p
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(
        urllib.request.urlopen(
            base + urllib.parse.quote(p, safe="") + "/raw?ref=" + commit, timeout=90
        ).read()
    )
    print(p, target.stat().st_size)
try:
    target = Path("research/article.pdf")
    target.write_bytes(
        urllib.request.urlopen(
            "https://orbit.dtu.dk/files/345410045/s41597-023-02808-6.pdf", timeout=30
        ).read()
    )
    print("article", target.stat().st_size)
except Exception as e:
    print("Article:", e)
