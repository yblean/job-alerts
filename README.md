# Singapore fresh-grad tech job alerts → Telegram

Checks every ~5 minutes, 24/7, and sends a Telegram message the moment a
new (or reposted) fresh-grad tech job in Singapore appears on:

- **LinkedIn**: logged-out job search, filtered to Singapore, Entry level, posted in the last 2 hours, newest first. 15 searches covering SWE, data, AI/ML, cloud/DevOps, security, QA, IT, BA/product, mobile, plus "graduate" / "fresh graduate" / "junior" searches.
- **MyCareersFuture**: Information Technology, "Fresh/entry level".
- **54 company career pages** with Singapore offices (Stripe, OpenAI, Airwallex, Binance, OKX, Databricks, Jane Street, Palantir, …). Companies often post here *before* LinkedIn.

Titles are filtered to tech roles, and senior, lead, manager, sales and intern
roles are dropped. Each job is alerted once; the same job found on another
site is skipped. Explicit grad roles get a 🎓, and reposts are marked 🔁.

Example alert:

```
🆕 NEW · LinkedIn
Graduate Software Engineer 🎓
🏢 Capgemini
📍 Singapore, Singapore
🕒 12 minutes ago
View & apply →
```

---

## Setup (about 10 minutes)

### 1. Create your Telegram bot

1. In Telegram, open **@BotFather** → send `/newbot` → choose a name and a username ending in `bot`.
2. BotFather replies with a **token** like `123456789:AAH...`. Keep it private.
3. Open your new bot and press **Start** (send it any message).
4. In a browser, open `https://api.telegram.org/bot<TOKEN>/getUpdates` (put your token in place of `<TOKEN>`).
   Find `"chat":{"id":123456789` and copy that number. It's your **chat id**.

### 2. Test it on your PC (optional)

Copy `.env.example` to `.env`, paste the token and chat id, then:

```powershell
pip install -r requirements.txt
python job_alerts.py --test-telegram
python job_alerts.py
```

The first check records the current jobs and sends a "bot is live" message.
After that you'll only get alerts for jobs that are new.
`python job_alerts.py --loop 0` keeps it running on your PC (Ctrl+C to stop).

### 3. Run it 24/7 for free on GitHub Actions

1. Create a free account at github.com if you don't have one.
2. Create a **new public repository** (e.g. `job-alerts`). It must be **public**, because
   GitHub Actions minutes are unlimited for public repos but a private repo
   would run out of free minutes in a few days. Your token stays secret
   (step 4). Only the code and the list of seen job ids are visible.
3. Push this folder to it:

   ```powershell
   git init -b main
   git add .
   git commit -m "feat: singapore job alerts bot"
   git remote add origin https://github.com/<your-username>/job-alerts.git
   git push -u origin main
   ```
   (`.env` is in `.gitignore`, so your token is **not** uploaded.)
4. In the repo: **Settings → Secrets and variables → Actions → New repository secret**. Add:
   - `TELEGRAM_BOT_TOKEN` = your bot token
   - `TELEGRAM_CHAT_ID` = your chat id
5. **Actions** tab → enable workflows if asked → **job-alerts** → **Run workflow**.
   You should get the "bot is live" message within ~3 minutes.

From then on it runs by itself. Each run checks every 5 minutes for ~28
minutes and a new run is queued every 20 minutes, so it never stops. Seen
jobs are saved to `state/seen.json` in the repo.

---

## Customising

Everything is in [config.py](config.py): LinkedIn searches and filters,
check interval, title filters, which companies to watch. Push the change
and the next run uses it. New companies' current jobs are recorded silently
the first time, so adding one won't flood you.

- **Getting too much noise?** Make `TECH_TITLE` stricter or add words to `NON_TECH_TITLE`.
- **Want internships too?** Set `INCLUDE_INTERNSHIPS = True` and add `"1"` to `LINKEDIN_EXPERIENCE_LEVELS`.
- **Want Associate-level roles from LinkedIn?** Add `"3"` to `LINKEDIN_EXPERIENCE_LEVELS`.

## Good to know

- **LinkedIn's terms prohibit scraping**, even logged out. This uses no
  account, so your LinkedIn profile can't be banned. The worst case is that
  LinkedIn blocks GitHub's servers, and then you get a ⚠️ Telegram message
  while the other sources keep working. If that happens, run it on your PC
  (`python job_alerts.py --loop 0`) instead. Home connections are blocked less often.
- GitHub's scheduler can start runs a few minutes late at busy times, and
  LinkedIn takes a few minutes to show new posts in search. Expect alerts
  within ~5–15 minutes of posting.
- GitHub pauses scheduled workflows in repos with no activity for 60 days.
  The bot's own commits should prevent that. If alerts ever stop, check the
  Actions tab and re-enable the workflow.
