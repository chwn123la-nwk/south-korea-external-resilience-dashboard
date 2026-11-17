# South Korea External Resilience Dashboard

**International Finance · Streamlit · GitHub Actions · No API keys**

**Question:** *Is South Korea becoming more resilient to external shocks, or does recent won weakness signal increasing external vulnerability?*

The dashboard has **six** indicators, matching the assignment requirement of 4–6 series. It compares high-frequency market conditions with slower-moving macroeconomic and external buffers. **A weaker won alone is not evidence of a crisis.** Interpretation depends on output growth, inflation, external financing and reserves. The dashboard is descriptive, not a causal test or credit-risk score.

## Selected indicators and exact public data feeds

| Indicator | Why chosen | Original source, code | Frequency / units | Public no-key machine-readable URL |
|---|---|---|---|---|
| USD/KRW exchange rate | Direct measure of recent won pressure | Federal Reserve H.10, hosted by FRED: `DEXKOUS` | Daily trading-day observations; **KRW per USD** | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXKOUS` |
| Korea 10-year government bond yield | Market financing conditions | OECD, hosted by FRED: `IRLTLT01KRM156N` | Monthly; percent per year | `https://fred.stlouisfed.org/graph/fredgraph.csv?id=IRLTLT01KRM156N` |
| Real GDP growth | Economy's ability to absorb shocks | World Bank WDI: `NY.GDP.MKTP.KD.ZG` | Annual; percent growth | `https://api.worldbank.org/v2/country/KOR/indicator/NY.GDP.MKTP.KD.ZG?format=json&per_page=1000` |
| CPI inflation | Domestic inflation pressures | World Bank WDI: `FP.CPI.TOTL.ZG` | Annual; percent inflation | `https://api.worldbank.org/v2/country/KOR/indicator/FP.CPI.TOTL.ZG?format=json&per_page=1000` |
| Current account | Foreign financing surplus/deficit | World Bank WDI / IMF balance-of-payments data: `BN.CAB.XOKA.GD.ZS` | Annual; percent of GDP | `https://api.worldbank.org/v2/country/KOR/indicator/BN.CAB.XOKA.GD.ZS?format=json&per_page=1000` |
| Total reserves incl. gold | External liquidity buffer (imperfect proxy) | World Bank WDI / IMF: `FI.RES.TOTL.CD` | Annual; current USD, shown as **USD billions** | `https://api.worldbank.org/v2/country/KOR/indicator/FI.RES.TOTL.CD?format=json&per_page=1000` |

These are **official or major international organization sources**; FRED is the Federal Reserve Bank of St. Louis. The original Korean 10-year yield is republished from OECD. No access token, API key, account creation or manual registration is required for the selected CSV and World Bank Indicators API routes. **This project does not call FRED's key-required `/fred/series/observations` API.**

Original series pages for manual verification:

- https://fred.stlouisfed.org/series/DEXKOUS
- https://fred.stlouisfed.org/series/IRLTLT01KRM156N
- https://data.worldbank.org/indicator/NY.GDP.MKTP.KD.ZG?locations=KR
- https://data.worldbank.org/indicator/FP.CPI.TOTL.ZG?locations=KR
- https://data.worldbank.org/indicator/BN.CAB.XOKA.GD.ZS?locations=KR
- https://data.worldbank.org/indicator/FI.RES.TOTL.CD?locations=KR

**Data frequency / currency convention:** A higher **KRW per USD** exchange rate means depreciation (won weakness), a lower number means appreciation. H.10 is a New York noon buying rate, not necessarily the Seoul close. A rising Korean government-bond yield may mean tighter financing conditions but is not, by itself, a sign of capital flight.

**Transformations:** The World Bank GDP and CPI series already report annual percentage changes (no homemade recomputation). Current account is published as a percent of GDP. Total reserves include gold and are divided by 1,000,000,000 to show USD **billions**; they are **not** the narrowly defined foreign-exchange-reserves-only series. FRED series are shown as published. No values are interpolated or filled forward. Chart date labels match source observations, and latest observation dates come directly from retrieved records.

**Historical window:** Download from 2000 onward and display 2005 onward by default. Adjustable start year in the sidebar. This allows comparison with 2008–09 and the pandemic. World Bank annual data can lag financial-market data by a year or more and may be revised. **Do not interpret a daily currency move using an annual current account value as if they were simultaneous.**

## Project structure

```text
app.py                         Streamlit UI, charts, refresh button, verification worksheet
 data_sources.py                Public downloads, checks, and durable snapshot CLI
requirements.txt                Dependencies
README.md                       This guide
.github/workflows/refresh.yml   Scheduled daily refresh
.gitignore
 data/.gitkeep                  Data directory placeholder
```

After a successful refresh, two **real-data** files are written under `data/`:

- `snapshot.json`: six series, latest observations and **last successful retrieval in UTC**
- `verification.csv`: automatically generated, **blank** independently checked source fields. It is overwritten on each scheduled update; keep your completed verification evidence separately.

No sample market values or fake successful refresh logs are bundled.

## Run locally

Python 3.11 recommended:

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python data_sources.py --save
streamlit run app.py
```

`python data_sources.py --save` downloads from all six services. If **any** download or validation fails, the CLI exits unsuccessfully rather than claiming a successful refresh. You can also start the dashboard without a snapshot: it will show a message and allow you to try **Refresh Data** interactively.

**Last successful data refresh** = time at which all six series were downloaded and validated, in UTC. **Latest observation date** = date/year for an individual series. They are deliberately different. The manual button retrieves data **for the current Streamlit session**; GitHub Actions writes the persistent copy.

## GitHub + Streamlit deployment

1. Create a GitHub repository, and push **all the files**, including `.github/workflows/refresh.yml`.
2. Under **Settings → Actions → General → Workflow permissions**, allow the workflow `GITHUB_TOKEN` to write repository contents. The workflow also explicitly requests `contents: write`.
3. In **Actions**, choose **Refresh official data → Run workflow**. Check for `result: SUCCESS` and six latest-observation dates in the logs; confirm `data/snapshot.json` is committed. Only successful runs can update the snapshot.
4. Open https://share.streamlit.io/, connect the GitHub repository, use `app.py` as the entry point, and deploy. No secrets are needed.
5. The GitHub schedule runs at **12:17 UTC daily**. GitHub scheduled jobs can be delayed or paused after repository inactivity. The manual *Run workflow* control remains an alternative. The app reads the last committed snapshot on startup; Streamlit's deployment rebuild/pull timing is managed by its hosting environment.
6. The **Refresh Data** button in the app makes a live request in your session, but **does not commit changes to GitHub**. The next scheduled GitHub run persists updates for all visitors.

If an API is unavailable temporarily, the workflow fails and keeps the previous successful GitHub snapshot. A failed in-app refresh displays an error and retains the last valid loaded data. This is preferable to fabricating data or resetting the success time.

## Assignment verification: one observation per series

1. Click **Download verification worksheet (CSV)** in the app (or open `data/verification.csv` after a scheduled run).
2. For **each of the six** rows, open the official series URL. Locate exactly the same observation date/period as in the dashboard.
3. Independently record the original provider-displayed value in **Original source value**, the date you checked and whether it matches the full-precision dashboard value after any *documented* unit conversion. FRED values can be compared with the FRED original page or CSV. For World Bank values, use the original country indicator page/API or downloaded official data. For reserves, note that the dashboard divides original USD by **1 billion**.
4. Attach or save the screenshot/official CSV excerpt. **A prefilled dashboard value is not independent verification**; no rows are marked checked automatically.
5. Take a screenshot of a successful **Actions → Refresh official data** job, including the `result: SUCCESS` log, and compare its UTC timestamp with the dashboard refresh header. The snapshot time proves completed retrieval, not independent accuracy.

**Submission package:** URL/screenshot of working dashboard, repository code, README setup + refresh instructions, completed six-row verification evidence, successful GitHub Actions log/screenshot and **memo ≤500 words**. The memo should (a) answer the research question, (b) state limitations, (c) describe the AI coding-agent workflow. The assignment specifically requires **4–6 relevant series**, not eight.

## Limitations

- Four World Bank series are annual, so these cannot diagnose a sudden shock in real time. The exchange rate is daily and 10-year yield is monthly, with different observation lags.
- Total international reserves *including gold* are not identical to the narrower foreign-exchange-only stock; neither ratio-to-imports nor short-term external debt is shown.
- Association is not causation. A won depreciation may reflect worldwide USD strength or interest-rate differentials rather than deteriorating Korean solvency.
- World Bank series can be revised and FRED/OECD publication periods can lag. The dashboard always displays the latest actual observations delivered by the live feeds.
- Internet access is required for refresh. This project was compiled and tested offline, but **the build environment could not complete a live six-series download**; before submission run the GitHub workflow and verify real output. Never claim a successful refresh before its log exists.
