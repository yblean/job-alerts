"""Settings for the job alert bot. Edit freely, then commit/push."""

# ─────────────────────────── How often ───────────────────────────
# Minutes between checks. 5 is a good balance; going lower raises the
# chance LinkedIn rate-limits you.
CHECK_EVERY_MINUTES = 5

# ─────────────────────────── LinkedIn ────────────────────────────
# Uses LinkedIn's logged-out ("guest") job search. No account, no login.
LINKEDIN_LOCATION = "Singapore"
LINKEDIN_GEO_ID = "102454443"  # LinkedIn's id for Singapore

# Only jobs posted in this window (LinkedIn's "Date posted" filter).
# 3600 = past hour. 7200 gives a safety margin if a check is delayed;
# already-seen jobs are never alerted twice, so a wider window is harmless.
LINKEDIN_POSTED_WITHIN_SECONDS = 7200

# LinkedIn "Experience level" filter: 1=Internship 2=Entry level
# 3=Associate 4=Mid-Senior 5=Director 6=Executive
LINKEDIN_EXPERIENCE_LEVELS = ["2"]

# LinkedIn "Job type": F=Full-time C=Contract P=Part-time T=Temporary
# I=Internship. Empty list = any.
LINKEDIN_JOB_TYPES = []

# LinkedIn "Remote" filter: 1=On-site 2=Remote 3=Hybrid. Empty = any.
LINKEDIN_WORK_TYPES = []

# One LinkedIn search per entry. "entry_level_filter": False skips the
# experience-level filter, for searches whose keyword already implies
# grad-level (many grad roles are tagged "Associate" or "Not applicable").
LINKEDIN_SEARCHES = [
    {"keywords": "software engineer"},
    {"keywords": "software developer"},
    {"keywords": "backend OR frontend OR full stack"},
    {"keywords": "data analyst OR data engineer OR data scientist"},
    {"keywords": "machine learning OR AI engineer"},
    {"keywords": "cloud OR devops OR site reliability"},
    {"keywords": "cybersecurity OR security engineer"},
    {"keywords": "QA OR test engineer OR automation"},
    {"keywords": "IT support OR IT executive OR system engineer"},
    {"keywords": "business analyst OR product analyst OR technology analyst"},
    {"keywords": "mobile OR iOS OR android developer"},
    {"keywords": "graduate", "entry_level_filter": False},
    {"keywords": "fresh graduate", "entry_level_filter": False},
    {"keywords": "junior developer OR junior engineer", "entry_level_filter": False},
    {"keywords": "graduate programme OR graduate program", "entry_level_filter": False},
]
LINKEDIN_MAX_PAGES = 3          # 10 results per page
LINKEDIN_DELAY_SECONDS = (2, 4)  # random pause between LinkedIn requests

# Telegram warning if LinkedIn fails this many checks in a row (blocked).
LINKEDIN_WARN_AFTER_FAILED_CHECKS = 6

# ─────────────────── MyCareersFuture (SG gov portal) ─────────────
MCF_ENABLED = True
MCF_CATEGORIES = ["Information Technology"]
MCF_POSITION_LEVELS = ["Fresh/entry level"]

# ─────────────────── Company career pages (ATS APIs) ──────────────
# These companies post here before (or instead of) LinkedIn.
# (platform, board id, display name). Only Singapore jobs are kept.
# To add one: open its careers page; if the URL looks like
#   boards.greenhouse.io/<id>, jobs.lever.co/<id> or jobs.ashbyhq.com/<id>
# add ("greenhouse"|"lever"|"ashby", "<id>", "Name").
COMPANY_BOARDS = [
    ("greenhouse", "okx", "OKX"),
    ("greenhouse", "binance", "Binance"),
    ("greenhouse", "stripe", "Stripe"),
    ("greenhouse", "databricks", "Databricks"),
    ("greenhouse", "towerresearchcapital", "Tower Research Capital"),
    ("greenhouse", "datadog", "Datadog"),
    ("greenhouse", "jumptrading", "Jump Trading"),
    ("greenhouse", "janestreet", "Jane Street"),
    ("greenhouse", "virtu", "Virtu Financial"),
    ("greenhouse", "riotgames", "Riot Games"),
    ("greenhouse", "purestorage", "Pure Storage"),
    ("greenhouse", "gitlab", "GitLab"),
    ("greenhouse", "anthropic", "Anthropic"),
    ("greenhouse", "xendit", "Xendit"),
    ("greenhouse", "coinbase", "Coinbase"),
    ("greenhouse", "pinterest", "Pinterest"),
    ("greenhouse", "gravitonresearchcapital", "Graviton Research Capital"),
    ("greenhouse", "ripple", "Ripple"),
    ("greenhouse", "agoda", "Agoda"),
    ("greenhouse", "zscaler", "Zscaler"),
    ("greenhouse", "mongodb", "MongoDB"),
    ("greenhouse", "twilio", "Twilio"),
    ("greenhouse", "thunes", "Thunes"),
    ("greenhouse", "okta", "Okta"),
    ("greenhouse", "fireblocks", "Fireblocks"),
    ("greenhouse", "elastic", "Elastic"),
    ("greenhouse", "optiverus", "Optiver"),
    ("greenhouse", "applovin", "AppLovin"),
    ("greenhouse", "rubrik", "Rubrik"),
    ("greenhouse", "figma", "Figma"),
    ("greenhouse", "gemini", "Gemini"),
    ("greenhouse", "roblox", "Roblox"),
    ("greenhouse", "akunacapital", "Akuna Capital"),
    ("greenhouse", "moloco", "Moloco"),
    ("greenhouse", "cloudflare", "Cloudflare"),
    ("greenhouse", "asana", "Asana"),
    ("greenhouse", "appier", "Appier"),
    ("greenhouse", "canonical", "Canonical"),
    ("greenhouse", "imc", "IMC Trading"),
    ("greenhouse", "flowtraders", "Flow Traders"),
    ("greenhouse", "wise", "Wise"),
    ("greenhouse", "scaleai", "Scale AI"),
    ("lever", "ninjavan", "Ninja Van"),
    ("lever", "crypto", "Crypto.com"),
    ("lever", "nium", "Nium"),
    ("lever", "palantir", "Palantir"),
    ("lever", "spotify", "Spotify"),
    ("ashby", "airwallex", "Airwallex"),
    ("ashby", "openai", "OpenAI"),
    ("ashby", "notion", "Notion"),
    ("ashby", "linear", "Linear"),
    ("ashby", "pragmatike", "Pragmatike"),
    ("ashby", "cohere", "Cohere"),
    ("ashby", "perplexity", "Perplexity"),
]
COMPANY_LOCATION_KEYWORD = "singapore"

# ─────────────────────────── Title filters ───────────────────────
# Regexes, case-insensitive, applied to every job title from every source.

# Must match: keeps tech roles, drops e.g. "Buyer", "Chef", "Technician".
TECH_TITLE = (
    r"software|developer|programmer|\bdata\b|analytics|machine learning|\bml\b|"
    r"\bai\b|artificial intelligence|\bllm|cloud|devops|devsecops|\bsre\b|"
    r"site reliability|security|cyber|infrastructure|network|\bsystems?\b|"
    r"platform|back[- ]?end|front[- ]?end|full[- ]?stack|mobile|\bios\b|android|"
    r"\bweb\b|\bqa\b|quality assurance|\btest|automation|\bit\b|technology|"
    r"\btech\b|technical|product (analyst|manager|owner|design)|\bux\b|\bui\b|"
    r"business analyst|solutions? engineer|application|database|blockchain|"
    r"\bquant|algorithm|computer|digital|\bsap\b|salesforce|\berp\b|crm|"
    r"hardware|embedded|firmware|electronics|semiconductor|research engineer|"
    r"research scientist|robotics|computer vision"
)

# Always drop: non-tech roles that happen to contain a tech word
# ("Account Executive, Platforms", "Sales Executive (IT)").
NON_TECH_TITLE = (
    r"account executive|account manager|\bsales\b|business development|"
    r"data entry|recruit|marketing|\bhr\b|human resource|accountant|"
    r"customer service|telemarket|driver|technician"
)

# Drop: too senior. (Overridden when GRAD_TITLE also matches, e.g.
# "Junior/Senior Software Engineer (open to fresh grads)".)
EXCLUDE_TITLE = (
    r"\bsenior\b|\bsr\.?\b|\bstaff\b|\blead\b|\bprincipal\b|\bmanager\b|"
    r"\bhead\b|\bdirector\b|\bvp\b|vice president|\barchitect\b|\bchief\b|"
    r"\bexpert\b|\bphd\b|\bmanaging\b|\bpartner\b|\bfellow\b|\bII\b|\bIII\b|\bIV\b"
)

# Marks a role as explicitly grad-level (gets a 🎓 in the alert).
GRAD_TITLE = (
    r"graduate|\bgrad\b|new grad|fresh|junior|\bjr\.?\b|entry|early career|"
    r"trainee|campus|university|\bassociate (software|engineer|developer|data)|"
    r"\bengineer I\b|\bdeveloper I\b|\bL1\b|apprentice"
)

# Internships are dropped unless this is True.
INCLUDE_INTERNSHIPS = False
INTERN_TITLE = r"\bintern\b|internship|\bco-?op\b|attachment|placement"

# ─────────────────── Experience check (job description) ───────────
# Before alerting, the bot reads the full job description and finds the
# years of experience it asks for ("3+ years", "minimum 2 years", ...).
# Jobs asking for more than this are dropped, unless the description says
# fresh grads are welcome. 1 keeps "0-2 yrs" and "1-3 yrs" roles.
MAX_YEARS_EXPERIENCE = 1

# Jobs whose description doesn't state any experience requirement and
# doesn't mention fresh grads / entry level. False = skip them (strict).
ALERT_WHEN_EXPERIENCE_UNCLEAR = False

# Max job descriptions to read per check (the rest wait for the next check).
MAX_DESCRIPTIONS_PER_CHECK = 60

# ─────────────────────────── Alerts ──────────────────────────────
MAX_ALERTS_PER_CHECK = 25  # anything beyond is summarised in one message

# A job with the same title + company seen within this many hours
# (on any source, under a different id) is treated as a duplicate and
# skipped; seen longer ago, it is alerted as a 🔁 repost.
DUPLICATE_WINDOW_HOURS = 72

# A LinkedIn job id that resurfaces in "recently posted" results at least
# this many hours after we first saw it is alerted as a 🔁 repost.
REPOST_MIN_AGE_HOURS = 24

# Forget jobs not seen for this many days (keeps the state file small).
FORGET_AFTER_DAYS = 45
