"""Weekly guard on GitHub Actions minutes (free plan: 2,000/month for private repos).

Plain English: adds up how long every job in this repo ran this calendar month, rounding
each job up to a whole minute the way GitHub bills, and warns on Telegram past the limit.
Uses only the run's own read-only GITHUB_TOKEN. The count is our estimate; GitHub's
Billing → Usage page is the official number.
"""
from __future__ import annotations

import datetime as dt
import math
import os
import sys

import requests

API = "https://api.github.com"
WARN_AT = 1500          # minutes; free allowance is 2,000


def _get(url: str, params: dict | None = None) -> dict:
    r = requests.get(url, params=params, timeout=30, headers={
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json"})
    r.raise_for_status()
    return r.json()


def job_minutes(started: str | None, completed: str | None) -> int:
    if not started or not completed:
        return 0
    a = dt.datetime.fromisoformat(started.replace("Z", "+00:00"))
    b = dt.datetime.fromisoformat(completed.replace("Z", "+00:00"))
    return max(1, math.ceil((b - a).total_seconds() / 60))


def month_minutes(repo: str, today: dt.date) -> int:
    since = today.replace(day=1).isoformat()
    total, page = 0, 1
    while True:
        runs = _get(f"{API}/repos/{repo}/actions/runs",
                    {"created": f">={since}", "per_page": 100, "page": page})["workflow_runs"]
        for run in runs:
            for j in _get(f"{API}/repos/{repo}/actions/runs/{run['id']}/jobs", {"per_page": 100})["jobs"]:
                total += job_minutes(j.get("started_at"), j.get("completed_at"))
        if len(runs) < 100:
            return total
        page += 1


# Scheduled jobs and the longest normal gap between successful runs (weekends included).
EXPECTED = {"benchmark_navs.yml": 4, "red_flags.yml": 4}   # quarterly report: once a quarter, failures alert


def stale_jobs(repo: str, now: dt.datetime) -> list[str]:
    """Silence must never mean broken: a scheduled job that stopped running sends no failure alert,
    so each Monday we check every scheduled job has succeeded recently. (GitHub also switches off
    schedules in repos with no activity for 60 days — this catches that too.)"""
    out = []
    for wf, days in EXPECTED.items():
        runs = _get(f"{API}/repos/{repo}/actions/workflows/{wf}/runs",
                    {"status": "success", "per_page": 1})["workflow_runs"]
        if not runs:
            out.append(f"{wf}: no successful run yet")
            continue
        last = dt.datetime.fromisoformat(runs[0]["updated_at"].replace("Z", "+00:00"))
        if now - last > dt.timedelta(days=days):
            out.append(f"{wf}: last success {last:%d %b %H:%M} UTC ({(now - last).days} days ago)")
    return out


def main() -> int:
    from v4 import alerts
    repo = os.environ["GITHUB_REPOSITORY"]
    stale = stale_jobs(repo, dt.datetime.now(dt.timezone.utc))
    if stale:
        alerts.send("⚠️ V4: scheduled job(s) have gone quiet — " + "; ".join(stale))
    used = month_minutes(repo, dt.date.today())
    print(f"Actions minutes this month (estimate): {used} of 2,000 free")
    if used >= WARN_AT:
        alerts.send(f"⚠️ V4: GitHub Actions has used about {used} of the 2,000 free minutes this month. "
                    "Nothing is charged (budget is $0), but jobs will stop if it reaches 2,000.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
