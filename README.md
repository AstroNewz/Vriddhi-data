# VRIDDHI वृद्धि — data backend

Free, scheduled data pipeline for the **VRIDDHI** Flutter app. It fetches
Indian large-cap data from Yahoo Finance and publishes four JSON files that the
app downloads. **Everything here runs for ₹0 on GitHub Actions.**

> **Educational, not investment advice.** VRIDDHI *screens* stocks with
> transparent rules — it does **not** predict prices.

## What it produces
| File | Contents |
|------|----------|
| `stocks.json` | Per-company fundamentals: price, P/E, debt-to-equity, profit trend, balance sheet, market share |
| `sectors.json` | Sector rollups + median P/E (the "cheap vs peers" yardstick) |
| `signals.json` | Rule-based scored picks with plain-English reasons & cautions |
| `technicals.json` | SMA-50, SMA-200, RSI, recent price history |

## How the score works (fully transparent — see `scoring.py`)
Score out of 10 = sum of four honest checks:
- **Value** (≤3): P/E below sector median → cheaper than peers
- **Debt** (≤3): low debt-to-equity → resilient balance sheet
- **Profit** (≤2): net profit rising over the available years
- **Technical** (≤2): price above its 200-day average

Each passed rule becomes a sentence in the app's "why" card. No black box.

## One-time setup (free)
1. Create a **public** GitHub repo named `vriddhi-data`.
2. Push these files to it:
   ```bash
   cd vriddhi-data
   git init && git add . && git commit -m "VRIDDHI data backend"
   git branch -M main
   git remote add origin https://github.com/<YOUR_USERNAME>/vriddhi-data.git
   git push -u origin main
   ```
3. In the repo: **Settings → Actions → General → Workflow permissions →
   "Read and write permissions"** (lets the bot commit refreshed JSON).
4. **Actions tab → "Refresh VRIDDHI data" → Run workflow** to generate the
   first dataset immediately (otherwise it runs automatically after market
   close, Mon–Fri).
5. In the app, set `kDataBaseUrl` in
   `lib/core/constants/app_constants.dart` to:
   ```
   https://raw.githubusercontent.com/<YOUR_USERNAME>/vriddhi-data/main
   ```
   Until you do, the app happily uses its bundled sample data.

## Run locally (optional)
```bash
pip install -r requirements.txt
python build_data.py     # writes the four JSON files into this folder
```

## Grow the universe
Add rows to `universe.py` — the builder and app scale automatically. Symbols
are the NSE ticker without the `.NS` suffix.

## Schedule
`.github/workflows/refresh.yml` runs at 17:30 IST on weekdays (after the NSE
close). The first run each month is automatically tagged `reportType: monthly`
for the monthly screening report. Free GitHub Actions minutes cover this many
times over.
