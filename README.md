# Gunpowder Falls Trout Stocking Watcher

Monitors the [MD DNR stocking API](https://webapps02.dnr.state.md.us/DNRTroutStockingAPI/api/RecentStockings) for Gunpowder Falls entries and sends email + push notifications when anything changes. Runs 3× per day via GitHub Actions.

**Live page:** `https://YOUR_USERNAME.github.io/troutcheck/`

---

## Setup

### 1. Push to GitHub

```bash
git init && git add . && git commit -m "Initial commit"
gh repo create troutcheck --public --source=. --push
```

### 2. Enable GitHub Pages

Repo → **Settings → Pages** → Source: **Deploy from branch** → branch: `main`, folder: `/ (root)`

### 3. Set up email (Gmail App Password)

1. Enable 2-Step Verification on your Google account
2. Go to **myaccount.google.com/apppasswords** and create an app password
3. Copy the 16-character password

### 4. Set up push notifications (OneSignal)

1. Create a free account at [onesignal.com](https://onesignal.com)
2. Create a new app → **Web** platform
3. Set your site URL to `https://YOUR_USERNAME.github.io/troutcheck/`
4. Copy the **App ID** and **REST API Key**
5. Replace `REPLACE_WITH_ONESIGNAL_APP_ID` in `index.html` with your App ID and push the change

### 5. Add GitHub Secrets

Repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Value |
|---|---|
| `ONESIGNAL_APP_ID` | From OneSignal dashboard |
| `ONESIGNAL_API_KEY` | REST API Key from OneSignal |
| `EMAIL_USERNAME` | Your Gmail address |
| `EMAIL_PASSWORD` | The 16-char Gmail App Password |
| `EMAIL_TO` | Where to send notification emails |

### 6. Run manually to save the baseline

Repo → **Actions → Check MD DNR Trout Stocking Page → Run workflow**

The first run saves a baseline with no notifications sent. All future runs compare against it.

---

## What it does

- Fetches Gunpowder Falls rows from the DNR stocking API
- Compares with the previous snapshot stored in `data/`
- Sends a push notification and email when rows are added or removed
- Commits updated data back to the repo so the GitHub Pages site stays current
- Email always sends (subject indicates changed vs. no change)
