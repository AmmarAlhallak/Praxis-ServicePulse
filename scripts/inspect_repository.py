import concurrent.futures
import json
import pathlib
import urllib.parse
import urllib.request

base = "https://lab.compute.dtu.dk/api/v4/projects/1804"
pathlib.Path("research").mkdir(exist_ok=True)
figshare = json.load(
    urllib.request.urlopen("https://api.figshare.com/v2/articles/24033324", timeout=30)
)
pathlib.Path("research/figshare_metadata.json").write_text(
    json.dumps(figshare, indent=2), encoding="utf-8"
)
project = json.load(urllib.request.urlopen(base, timeout=30))
pathlib.Path("research/gitlab_project.json").write_text(
    json.dumps(project, indent=2), encoding="utf-8"
)
commit = json.load(urllib.request.urlopen(base + "/repository/commits/main"))
pathlib.Path("research/gitlab_commit.json").write_text(json.dumps(commit, indent=2))
all = []
page = 1
while True:
    d = json.load(
        urllib.request.urlopen(
            base + f"/repository/tree?ref={commit['id']}&recursive=true&per_page=100&page={page}",
            timeout=30,
        )
    )
    all += d
    if len(d) < 100:
        break
    page += 1
pathlib.Path("research/gitlab_tree.json").write_text(json.dumps(all, indent=2))
files = [x["path"] for x in all if x["type"] == "blob"]
print("TOTAL", len(all), "FILES", len(files))
print("\n".join(x for x in files if not x.startswith("data/raw_data/")))
selected = [
    x
    for x in files
    if x.endswith((".py", ".md", ".txt", ".yml", ".yaml", ".toml", ".xlsx", ".csv"))
    or "LICENSE" in x.upper()
]


def get(p):
    target = pathlib.Path("research/reference") / p
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        target.write_bytes(
            urllib.request.urlopen(
                base
                + "/repository/files/"
                + urllib.parse.quote(p, safe="")
                + "/raw?ref="
                + commit["id"],
                timeout=60,
            ).read()
        )
    except Exception as e:
        print("FAIL", p, e)


with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    list(pool.map(get, selected))
print("COMMIT", commit["id"], "SAVED", len(selected))
