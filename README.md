# Yuichi AI Terminal

**Active project:** Yuichi's personal market and portfolio dashboard.

Live app: https://yuichi-ai-terminal-hdtwdvm88r8wuxwzeqsupb.streamlit.app

The repository's `main` branch contains the application source. A deployed app may use an earlier commit; check the Streamlit deployment settings before changing its entry point.

## What it does

Displays market prices, portfolio information, a market calendar, research, and a watchlist. Optional Claude-generated market commentary requires an Anthropic API key.

## Files explained

| File or folder | Purpose |
| --- | --- |
| `app.py` | Main screen and application flow; Streamlit entry point |
| `core/` | Market, portfolio, and optional AI logic |
| `components/` | Reusable display helpers |
| `data/market_calendar.json` | Editable market calendar |
| `data/portfolio.json` | Portfolio holdings and cost bases |
| `data/regime_history.csv` | Market-regime history; can change during use |
| `requirements.txt` | Python packages needed to run the app |
| `.devcontainer/` | GitHub Codespaces development setup |
| `push_error.txt` | Preserved historical diagnostic log; not needed to run the app |

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

For optional AI commentary, set `ANTHROPIC_API_KEY` in the environment before starting the app. Never put a real key in source files. The current AI module reads an environment variable; it does not load a `.env` file automatically.

## Deployment and data

For Streamlit, use `app.py` as the entry point and keep credentials in the hosting configuration, outside GitHub. Keep required packages in `requirements.txt`.

The tracked portfolio file contains holdings and cost bases. In a public repository, visitors can read that data. Do not add account credentials, bank exports, or private household records.

`.gitignore` prevents matching new local files from being added accidentally. It does not remove files already committed or erase history. The separately ignored `news_briefing.py` automation is not backed up by this repository.

## Maintenance

Edit app code for behavior, the calendar JSON for calendar updates, and the portfolio JSON for holdings. Commit related changes together with a clear description. Preserve working commits before larger changes.

## Yuichi's app directory

| App | Repository | Where it runs |
| --- | --- | --- |
| Yuichi AI Terminal | [yuichi-ai-terminal](https://github.com/braveoneu1-dot/yuichi-ai-terminal) | Streamlit |
| Household Finance / Harbor | [household-finance-app](https://github.com/braveoneu1-dot/household-finance-app) — private; source import pending | ChatGPT Sites |
| Jackの英語ジャッジ | [jack-english-judge](https://github.com/braveoneu1-dot/jack-english-judge) | Streamlit |
| Jack American Mode | [jack-american-mode](https://github.com/braveoneu1-dot/jack-american-mode) — private; source import pending | ChatGPT Sites |

Verified October 15, 2026: both private repositories exist, but currently contain only placeholder documentation. Their application source has not yet been imported. Sites keeps its own source and saved versions; those are separate from GitHub.

