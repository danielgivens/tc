# MD DNR Trout Stocking Watcher

Monitors the [Maryland DNR Trout Stocking page](https://dnr.maryland.gov/fisheries/pages/trout/stocking.aspx) for changes and sends push + email notifications.

Runs automatically via GitHub Actions 3× per day (roughly 3am, 9am, 3pm ET).

---

## Setup

### 1. Create a GitHub repository

Push this folder to a new GitHub repo (public or private both work).

```bash
cd troutcheck
git init
git add .
git commit -m "Initial commit"
gh repo create troutcheck --public --source=. --push
# or use the GitHub website to create the repo and follow the push instructions
```

---

### 2. Set up push notifications (ntfy.sh)

[ntfy.sh](https://ntfy.sh) is a free push notification service — no account needed.

1. **Pick a unique topic name** — something hard to guess, like `maryland-trout-abc123`. Anyone who knows the topic can subscribe, so treat it like a password.
2. **Subscribe on your devices:**
   - **Phone:** Install the [ntfy app](https://ntfy.sh/#subscribe) (iOS / Android), tap `+`, enter your topic name.
   - **Desktop:** Open `https://ntfy.sh/YOUR_TOPIC` in a browser and allow notifications.
3. Add your topic name as a GitHub secret (see step 4).

---

### 3. Set up email notifications (Gmail)

You need a Gmail account and an **App Password** (not your regular password).

1. Go to your Google Account → **Security** → **2-Step Verification** (must be enabled).
2. Then go to **Security** → **App passwords**.
3. Create a new app password (name it anything, e.g. "Trout Watcher").
4. Copy the 16-character password — you'll need it in the next step.

> If you'd rather use a different email provider, update `server_address` and `server_port` in `.github/workflows/check-stocking.yml`.

---

### 4. Add GitHub Secrets

In your GitHub repo, go to **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret name | Value |
|---|---|
| `NTFY_TOPIC` | Your unique ntfy.sh topic name |
| `EMAIL_USERNAME` | Your Gmail address (e.g. `you@gmail.com`) |
| `EMAIL_PASSWORD` | The 16-character Gmail App Password from step 3 |
| `EMAIL_TO` | The address to send notifications to (can be the same as above) |

---

### 5. Run it manually to create the baseline

After pushing to GitHub:

1. Go to your repo → **Actions** tab.
2. Click **Check MD DNR Trout Stocking Page** → **Run workflow**.

This first run saves a baseline snapshot. No notification is sent. Future runs will compare against this baseline and notify you when anything changes.

---

## How it works

```
GitHub Actions (cron: 3x/day)
  └── scripts/check_page.py
        ├── Fetch the DNR stocking page
        ├── Strip navigation/scripts, extract main content
        ├── SHA-256 hash the text
        ├── Compare with data/last_hash.txt
        └── If different:
              ├── Send push via ntfy.sh
              ├── Send email via Gmail
              └── Commit updated snapshot back to repo
```

The `data/` directory stores:
- `last_hash.txt` — SHA-256 of the last seen content
- `last_content.txt` — full text of the last seen page (used to generate diff summaries)

---

## Customizing the schedule

Edit the `cron` line in `.github/workflows/check-stocking.yml`:

```yaml
- cron: '0 7,13,19 * * *'  # 7am, 1pm, 7pm UTC = 3am, 9am, 3pm ET
```

Use [crontab.guru](https://crontab.guru) to build a custom schedule.
