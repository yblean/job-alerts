#!/usr/bin/env python3
"""Singapore fresh-grad tech job alerts, sent to Telegram.

Sources: LinkedIn (logged-out job search), MyCareersFuture, and company
career boards on Greenhouse / Lever / Ashby. See README.md for setup.

  python job_alerts.py                 one check
  python job_alerts.py --loop 0        check forever (every CHECK_EVERY_MINUTES)
  python job_alerts.py --loop 28       keep checking for 28 minutes (GitHub Actions)
  python job_alerts.py --dry-run       print alerts instead of sending
  python job_alerts.py --test-telegram send one test message
"""
import argparse
import html
import json
import os
import random
import re
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import sys

import requests
from bs4 import BeautifulSoup

import config as C

for _stream in (sys.stdout, sys.stderr):  # Windows consoles default to cp1252: no emoji
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / "state" / "seen.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})

TECH_RE = re.compile(C.TECH_TITLE, re.I)
EXCLUDE_RE = re.compile(C.EXCLUDE_TITLE, re.I)
NON_TECH_RE = re.compile(C.NON_TECH_TITLE, re.I)
GRAD_RE = re.compile(C.GRAD_TITLE, re.I)
INTERN_RE = re.compile(C.INTERN_TITLE, re.I)

SOURCE_LABEL = {"linkedin": "LinkedIn", "mcf": "MyCareersFuture",
                "greenhouse": "Company site", "lever": "Company site",
                "ashby": "Company site"}


def log(*args):
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), *args, flush=True)


@dataclass
class Job:
    feed: str          # e.g. "linkedin", "mcf", "greenhouse:stripe"
    id: str
    title: str
    company: str
    location: str
    url: str
    posted_text: str = ""  # human-readable, e.g. "12 minutes ago"
    posted_key: str = ""   # comparable posting date, used to spot reposts
    extra: str = ""        # e.g. salary

    @property
    def source(self):
        return self.feed.split(":")[0]

    @property
    def uid(self):
        return f"{self.feed}:{self.id}"


# ─────────────────────────── Filters ───────────────────────────

def title_ok(title):
    if not C.INCLUDE_INTERNSHIPS and INTERN_RE.search(title):
        return False
    if not TECH_RE.search(title) or NON_TECH_RE.search(title):
        return False
    if EXCLUDE_RE.search(title) and not GRAD_RE.search(title):
        return False
    return True


def norm(s):
    s = s.lower()
    s = re.sub(r"\b(pte|ltd|limited|private|inc|llp|llc|corp|corporation|"
               r"co|company|group|holdings|singapore|sg)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", "", s)


# ─────────────────────────── LinkedIn ───────────────────────────

LI_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"


def li_get(params):
    """Returns page HTML, "" when there are no more results, None on failure."""
    for attempt in range(3):
        status = "error"
        try:
            r = SESSION.get(LI_URL, params=params, timeout=25)
            status = r.status_code
            if r.status_code == 200:
                return r.text
            if r.status_code in (400, 404):  # past the last page
                return ""
        except requests.RequestException as e:
            status = type(e).__name__
        wait = 10 * (2 ** attempt) + random.uniform(0, 5)
        log(f"  LinkedIn {status} for '{params.get('keywords')}', retry in {wait:.0f}s")
        time.sleep(wait)
    return None


def fetch_linkedin():
    jobs, ok, failed = [], 0, 0
    for search in C.LINKEDIN_SEARCHES:
        for page in range(C.LINKEDIN_MAX_PAGES):
            params = {
                "keywords": search["keywords"],
                "location": C.LINKEDIN_LOCATION,
                "geoId": C.LINKEDIN_GEO_ID,
                "f_TPR": f"r{C.LINKEDIN_POSTED_WITHIN_SECONDS}",
                "sortBy": "DD",
                "start": page * 10,
            }
            if search.get("entry_level_filter", True) and C.LINKEDIN_EXPERIENCE_LEVELS:
                params["f_E"] = ",".join(C.LINKEDIN_EXPERIENCE_LEVELS)
            if C.LINKEDIN_JOB_TYPES:
                params["f_JT"] = ",".join(C.LINKEDIN_JOB_TYPES)
            if C.LINKEDIN_WORK_TYPES:
                params["f_WT"] = ",".join(C.LINKEDIN_WORK_TYPES)

            text = li_get(params)
            time.sleep(random.uniform(*C.LINKEDIN_DELAY_SECONDS))
            if text is None:
                failed += 1
                break
            ok += 1
            cards = BeautifulSoup(text, "html.parser").select("div.base-card")
            for card in cards:
                job = parse_li_card(card)
                if job:
                    jobs.append(job)
            if len(cards) < 10:
                break
    return jobs, ok, failed


def parse_li_card(card):
    m = re.search(r"jobPosting:(\d+)", card.get("data-entity-urn", ""))
    title_el = card.select_one("h3.base-search-card__title")
    if not m or not title_el:
        return None
    job_id = m.group(1)
    company_el = card.select_one("h4.base-search-card__subtitle")
    loc_el = card.select_one(".job-search-card__location")
    time_el = card.select_one("time")
    return Job(
        feed="linkedin",
        id=job_id,
        title=title_el.get_text(" ", strip=True),
        company=company_el.get_text(" ", strip=True) if company_el else "",
        location=loc_el.get_text(" ", strip=True) if loc_el else "",
        url=f"https://www.linkedin.com/jobs/view/{job_id}/",
        posted_text=time_el.get_text(" ", strip=True) if time_el else "",
        posted_key=time_el.get("datetime", "") if time_el else "",
    )


# ─────────────────────── MyCareersFuture ───────────────────────

def fetch_mcf():
    body = {"sessionId": "", "search": "", "categories": C.MCF_CATEGORIES,
            "positionLevels": C.MCF_POSITION_LEVELS, "sortBy": ["new_posting_date"]}
    r = SESSION.post("https://api.mycareersfuture.gov.sg/v2/search?limit=100&page=0",
                     json=body, timeout=30)
    r.raise_for_status()
    jobs = []
    for j in r.json().get("results", []):
        meta = j.get("metadata") or {}
        company = (j.get("hiringCompany") or j.get("postedCompany") or {}).get("name", "")
        sal = j.get("salary") or {}
        extra = ""
        if sal.get("minimum") and not meta.get("isHideSalary"):
            extra = f"${sal['minimum']:,}–{sal.get('maximum', sal['minimum']):,} / month"
        jobs.append(Job(
            feed="mcf",
            id=j["uuid"],
            title=j.get("title", ""),
            company=company.title(),
            location="Singapore",
            url=meta.get("jobDetailsUrl") or f"https://www.mycareersfuture.gov.sg/job/{j['uuid']}",
            posted_text=f"Posted {meta.get('newPostingDate', '')}",
            posted_key=meta.get("newPostingDate", ""),
            extra=extra,
        ))
    return jobs


# ─────────────────── Company boards (ATS APIs) ───────────────────

def in_sg(*locations):
    kw = C.COMPANY_LOCATION_KEYWORD
    return any(kw in (loc or "").lower() for loc in locations)


def fetch_board(board):
    platform, token, name = board
    feed = f"{platform}:{token}"
    jobs = []
    if platform == "greenhouse":
        r = SESSION.get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs", timeout=30)
        r.raise_for_status()
        for j in r.json().get("jobs", []):
            loc = (j.get("location") or {}).get("name", "")
            if in_sg(loc):
                jobs.append(Job(feed, str(j["id"]), j.get("title", ""), name, loc,
                                j.get("absolute_url", "")))
    elif platform == "lever":
        r = SESSION.get(f"https://api.lever.co/v0/postings/{token}?mode=json", timeout=30)
        r.raise_for_status()
        for j in r.json():
            cats = j.get("categories") or {}
            locs = [cats.get("location", "")] + list(cats.get("allLocations") or [])
            if in_sg(*locs):
                jobs.append(Job(feed, j["id"], j.get("text", ""), name,
                                cats.get("location", ""), j.get("hostedUrl", "")))
    elif platform == "ashby":
        r = SESSION.get(f"https://api.ashbyhq.com/posting-api/job-board/{token}", timeout=30)
        r.raise_for_status()
        for j in r.json().get("jobs", []):
            if j.get("isListed") is False:
                continue
            locs = [j.get("location", "")] + [s.get("location", "") for s in j.get("secondaryLocations") or []]
            if in_sg(*locs):
                jobs.append(Job(feed, j["id"], j.get("title", ""), name,
                                j.get("location", ""), j.get("jobUrl", "")))
    else:
        raise ValueError(f"unknown platform {platform}")
    return jobs


# ─────────────────────────── Telegram ───────────────────────────

class Telegram:
    def __init__(self, token, chat_id, dry_run=False):
        self.token, self.chat_id, self.dry_run = token, chat_id, dry_run

    def send(self, text):
        if self.dry_run:
            print("\n" + text + "\n" + "─" * 40, flush=True)
            return True
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": text, "parse_mode": "HTML",
                   "disable_web_page_preview": True}
        for _ in range(4):
            try:
                r = requests.post(url, json=payload, timeout=20)
            except requests.RequestException as e:
                log(f"  Telegram request failed ({type(e).__name__})")  # never log the URL: it holds the token
                time.sleep(5)
                continue
            if r.status_code == 429:
                time.sleep(r.json().get("parameters", {}).get("retry_after", 5) + 1)
                continue
            if r.ok:
                time.sleep(1.1)  # stay under Telegram's ~1 msg/sec per chat
                return True
            log(f"  Telegram error {r.status_code}: {r.text[:200]}")
            return False
        return False


def fmt_alert(job, kind):
    e = html.escape
    head = "🔁 <b>REPOSTED</b>" if kind == "repost" else "🆕 <b>NEW</b>"
    grad = " 🎓" if GRAD_RE.search(job.title) else ""
    lines = [f"{head} · {SOURCE_LABEL.get(job.source, job.source)}",
             f"<b>{e(job.title)}</b>{grad}",
             f"🏢 {e(job.company)}"]
    if job.location:
        lines.append(f"📍 {e(job.location)}")
    if job.posted_text:
        lines.append(f"🕒 {e(job.posted_text)}")
    if job.extra:
        lines.append(f"💰 {e(job.extra)}")
    lines.append(f'<a href="{e(job.url, quote=True)}">View &amp; apply →</a>')
    return "\n".join(lines)


# ─────────────────────────── State ───────────────────────────

def load_state():
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    else:
        state = {}
    state.setdefault("jobs", {})      # uid -> {first, last, alerted, posted}
    state.setdefault("titles", {})    # normalised title|company -> first seen
    state.setdefault("seeded", [])    # feeds whose backlog was recorded silently
    state.setdefault("meta", {})
    return state


def save_state(state):
    cutoff = time.time() - C.FORGET_AFTER_DAYS * 86400
    state["jobs"] = {k: v for k, v in state["jobs"].items() if v["last"] >= cutoff}
    state["titles"] = {k: v for k, v in state["titles"].items() if v >= cutoff}
    STATE_FILE.parent.mkdir(exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, separators=(",", ":"), sort_keys=True), encoding="utf-8")
    tmp.replace(STATE_FILE)


# ─────────────────────────── One check ───────────────────────────

def run_check(state, tg):
    t0 = time.time()
    feeds_ok = set()
    all_jobs = []

    boards = C.COMPANY_BOARDS
    with ThreadPoolExecutor(max_workers=10) as pool:
        board_futs = [(b, pool.submit(fetch_board, b)) for b in boards]
        mcf_fut = pool.submit(fetch_mcf) if C.MCF_ENABLED else None
        li_jobs, li_ok, li_failed = fetch_linkedin()  # sequential, polite

        for (platform, token, _), fut in board_futs:
            try:
                all_jobs += fut.result()
                feeds_ok.add(f"{platform}:{token}")
            except Exception as e:
                log(f"  {platform}:{token} failed: {type(e).__name__} {str(e)[:120]}")
        if mcf_fut:
            try:
                all_jobs += mcf_fut.result()
                feeds_ok.add("mcf")
            except Exception as e:
                log(f"  MyCareersFuture failed: {type(e).__name__} {str(e)[:120]}")

    all_jobs += li_jobs
    if li_ok:
        feeds_ok.add("linkedin")

    # LinkedIn health: warn once if it keeps failing (likely blocked).
    meta = state["meta"]
    if li_ok == 0 and li_failed:
        meta["li_fail_streak"] = meta.get("li_fail_streak", 0) + 1
        if meta["li_fail_streak"] == C.LINKEDIN_WARN_AFTER_FAILED_CHECKS:
            tg.send("⚠️ LinkedIn has failed the last "
                    f"{C.LINKEDIN_WARN_AFTER_FAILED_CHECKS} checks (probably rate-limited). "
                    "Other sources still running; I'll tell you when LinkedIn is back.")
    else:
        if meta.get("li_fail_streak", 0) >= C.LINKEDIN_WARN_AFTER_FAILED_CHECKS:
            tg.send("✅ LinkedIn is working again.")
        meta["li_fail_streak"] = 0

    # Decide what to alert on.
    now = time.time()
    seeded = set(state["seeded"])
    alerts = []  # (job, kind, title_key, previous_title_seen)
    seen_this_check = set()
    kept = 0
    for job in all_jobs:
        if job.uid in seen_this_check or not title_ok(job.title):
            continue
        seen_this_check.add(job.uid)
        kept += 1
        silent = job.feed not in seeded
        tkey = f"{norm(job.title)}|{norm(job.company)}"
        rec = state["jobs"].get(job.uid)

        if rec:
            repost = False
            if job.source == "mcf" and job.posted_key and rec.get("posted") and job.posted_key > rec["posted"]:
                repost = True  # employer reposted: new posting date, same job
            if (job.source == "linkedin"
                    and now - rec["first"] > C.REPOST_MIN_AGE_HOURS * 3600
                    and now - rec.get("alerted", 0) > C.REPOST_MIN_AGE_HOURS * 3600):
                repost = True  # old job id is back in "recently posted"
            rec["last"] = now
            if job.posted_key:
                rec["posted"] = max(job.posted_key, rec.get("posted") or "")
            if repost and not silent:
                rec["alerted"] = now
                alerts.append((job, "repost", None, None))
            continue

        prev = state["titles"].get(tkey)
        state["jobs"][job.uid] = {"first": now, "last": now, "alerted": now, "posted": job.posted_key}
        state["titles"].setdefault(tkey, now)
        if silent:
            continue
        if prev and now - prev < C.DUPLICATE_WINDOW_HOURS * 3600:
            continue  # same job already alerted from another source / listing
        alerts.append((job, "repost" if prev else "new", tkey, prev))

    # Send.
    sent = 0
    for i, (job, kind, tkey, prev) in enumerate(alerts):
        if i >= C.MAX_ALERTS_PER_CHECK:
            rest = alerts[i:]
            names = "\n".join(f"• {html.escape(j.title)} — {html.escape(j.company)}" for j, *_ in rest[:30])
            tg.send(f"➕ <b>{len(rest)} more new jobs</b> this check:\n{names}")
            break
        if tg.send(fmt_alert(job, kind)):
            sent += 1
        elif kind == "new":
            # Not delivered: forget it so the next check retries.
            state["jobs"].pop(job.uid, None)
            if prev is None:
                state["titles"].pop(tkey, None)

    newly_seeded = feeds_ok - seeded
    state["seeded"] = sorted(seeded | feeds_ok)
    log(f"check done in {time.time() - t0:.0f}s: {len(all_jobs)} jobs fetched, {kept} match filters, "
        f"{sent} alerts sent | LinkedIn {li_ok} ok / {li_failed} failed | "
        f"{len(feeds_ok)} sources ok" + (f" | {len(newly_seeded)} new sources recorded silently" if newly_seeded else ""))
    return newly_seeded, kept


# ─────────────────────────── Main ───────────────────────────

def load_dotenv():
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--loop", type=float, metavar="MINUTES",
                    help="keep checking for this many minutes (0 = forever)")
    ap.add_argument("--dry-run", action="store_true", help="print alerts instead of sending them")
    ap.add_argument("--test-telegram", action="store_true", help="send a test message and exit")
    args = ap.parse_args()

    load_dotenv()
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not args.dry_run and not (token and chat_id):
        raise SystemExit("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID (or use --dry-run). See README.md.")
    tg = Telegram(token, chat_id, dry_run=args.dry_run)

    if args.test_telegram:
        ok = tg.send("👋 Test message from your Singapore job alert bot. It works!")
        raise SystemExit(0 if ok else 1)

    state = load_state()
    interval = C.CHECK_EVERY_MINUTES * 60
    deadline = None if not args.loop else time.time() + args.loop * 60

    while True:
        started = time.time()
        first_ever = not state["seeded"]
        try:
            newly_seeded, kept = run_check(state, tg)
            if first_ever and newly_seeded:
                tg.send(f"✅ <b>Job alert bot is live</b>\nWatching {len(newly_seeded)} sources "
                        f"(LinkedIn, MyCareersFuture, {len(C.COMPANY_BOARDS)} company career pages) "
                        f"for Singapore fresh-grad tech roles. {kept} current jobs recorded; "
                        f"you'll be alerted to anything new or reposted from now on.")
        except Exception:
            log("check crashed:\n" + traceback.format_exc())
        save_state(state)

        if args.loop is None:
            break
        next_start = started + interval
        if deadline and next_start > deadline:
            break
        time.sleep(max(0, next_start - time.time()))


if __name__ == "__main__":
    main()
