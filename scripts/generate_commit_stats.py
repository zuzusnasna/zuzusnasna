import os
import json
import urllib.request
import urllib.error
from collections import Counter
from datetime import datetime, timezone, timedelta
from xml.sax.saxutils import escape

USERNAME = "zuzusnasna"
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API = "https://api.github.com"
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "commit-time-stats-generator",
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

def get_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

counts = Counter()
total = 0
try:
    repos = get_json(f"{API}/users/{USERNAME}/repos?type=owner&sort=updated&per_page=100")
    for repo in repos:
        if repo.get("fork") or repo.get("archived"):
            continue
        full_name = repo["full_name"]
        page = 1
        # Sample up to 100 recent commits per repository to stay within API limits.
        while page <= 2:
            url = f"{API}/repos/{full_name}/commits?author={USERNAME}&per_page=100&page={page}"
            try:
                commits = get_json(url)
            except urllib.error.HTTPError as exc:
                if exc.code in (403, 404, 409):
                    break
                raise
            if not commits:
                break
            for item in commits:
                date = (item.get("commit", {}).get("author") or {}).get("date")
                if not date:
                    continue
                try:
                    # Commit timestamps include their timezone; display hour in Korea time.
                    dt = datetime.fromisoformat(date.replace("Z", "+00:00")).astimezone(timezone(timedelta(hours=9)))
                    counts[dt.hour] += 1
                    total += 1
                except ValueError:
                    continue
            if len(commits) < 100:
                break
            page += 1
except Exception as exc:
    print(f"Unable to retrieve commit history: {exc}")
    raise

width, height = 920, 390
left, top, chart_w, chart_h = 70, 105, 800, 190
max_value = max(counts.values(), default=1)
bar_w = 22
gap = (chart_w - 24 * bar_w) / 23
parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
    '<defs><linearGradient id="bar" x1="0" y1="1" x2="0" y2="0"><stop offset="0%" stop-color="#2563eb"/><stop offset="100%" stop-color="#38bdf8"/></linearGradient>',
    '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#0f172a"/><stop offset="100%" stop-color="#172554"/></linearGradient></defs>',
    '<rect width="100%" height="100%" rx="18" fill="url(#bg)"/>',
    '<text x="34" y="43" fill="#f8fafc" font-family="Segoe UI,Arial,sans-serif" font-size="23" font-weight="700">COMMIT TIME DISTRIBUTION</text>',
    '<text x="35" y="70" fill="#cbd5e1" font-family="Segoe UI,Arial,sans-serif" font-size="13">Owned public repositories · timestamps shown in Korea Standard Time (KST)</text>',
    f'<text x="{width-34}" y="43" text-anchor="end" fill="#7dd3fc" font-family="Segoe UI,Arial,sans-serif" font-size="18" font-weight="700">{total:,} commits sampled</text>',
]
for tick in (0, 0.5, 1):
    y = top + chart_h * (1 - tick)
    parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left+chart_w}" y2="{y:.1f}" stroke="#334155" stroke-width="1"/>')
for hour in range(24):
    value = counts[hour]
    h = (value / max_value) * chart_h if max_value else 0
    x = left + hour * (bar_w + gap)
    y = top + chart_h - h
    parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w}" height="{max(3,h):.1f}" rx="5" fill="url(#bar)"/>')
    if value:
        parts.append(f'<text x="{x+bar_w/2:.1f}" y="{max(top-5,y-8):.1f}" text-anchor="middle" fill="#e2e8f0" font-family="Segoe UI,Arial,sans-serif" font-size="10">{value}</text>')
    if hour % 2 == 0:
        parts.append(f'<text x="{x+bar_w/2:.1f}" y="{top+chart_h+23}" text-anchor="middle" fill="#cbd5e1" font-family="Segoe UI,Arial,sans-serif" font-size="11">{hour:02d}</text>')
parts += [
    f'<text x="{left+chart_w/2}" y="{top+chart_h+49}" text-anchor="middle" fill="#94a3b8" font-family="Segoe UI,Arial,sans-serif" font-size="12">Hour of day (KST · UTC+9)</text>',
    '<text x="35" y="365" fill="#94a3b8" font-family="Segoe UI,Arial,sans-serif" font-size="11">Recent commits from owned public repositories; capped sample per repository.</text>',
    '</svg>'
]
os.makedirs("assets", exist_ok=True)
with open("assets/commit-time.svg", "w", encoding="utf-8") as file:
    file.write("\n".join(parts))
print(f"Generated commit-time chart from {total} commits.")
