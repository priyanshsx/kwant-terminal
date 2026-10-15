# Quartermaster

**Quantitative analysis for crypto assets, built with Python and Streamlit.**

Quartermaster downloads historical daily market data for a set of crypto assets, audits that data for integrity problems, and, only if the data passes, computes risk and return metrics and renders them as interactive Plotly charts. You choose the asset and the timeframe.

**Live app:** [https://kwant-terminal.streamlit.app/](https://app.quartermasterlabs.com/)

> **Disclaimer:** Quartermaster is for educational and research purposes only. It is not financial advice. Past performance does not predict future results.

---

## Table of contents

1. [What it does](#what-it-does)
2. [How the pipeline works](#how-the-pipeline-works)
3. [Methodology](#methodology)
   - [Data source](#1-data-source)
   - [Data integrity checks (Tick Inspector)](#2-data-integrity-checks-tick-inspector)
   - [Return calculations](#3-return-calculations)
   - [Moving averages](#4-moving-averages)
   - [Rolling volatility](#5-rolling-volatility)
   - [Cumulative return](#6-cumulative-return)
   - [Drawdown and maximum drawdown](#7-drawdown-and-maximum-drawdown)
   - [Distribution statistics](#8-distribution-statistics-skewness-and-excess-kurtosis)
   - [Returns histogram](#9-returns-histogram)
4. [Dashboard layout](#dashboard-layout)
5. [Engineering notes](#engineering-notes)
6. [Limitations and caveats](#limitations-and-caveats)
7. [Running locally](#running-locally)
8. [Project history](#project-history)
9. [Roadmap](#roadmap)

---

## What it does

- **Source** historical daily OHLCV (Open, High, Low, Close, Volume) data for a curated list of crypto assets from Yahoo Finance.
- **Audit** the data before any math is done, and halt the analysis if the data is corrupted.
- **Analyze** the data with returns, moving averages, rolling volatility, cumulative return, drawdown, and distribution statistics.
- **Visualize** the results in a dashboard with a metrics tape and four interactive charts.

Supported assets: BTC-USD, ETH-USD, SOL-USD, HYPE-USD, USDT-USD, BNB-USD, XRP-USD, ZEC-USD, WETH-USD, TRX-USD, NEAR-USD, LSK-USD.

---

## How the pipeline works

```
Select asset + dates  ->  Download  ->  Tick Inspector  ->  Quant Analyzer  ->  Dashboard
                                              |
                                         bad data?
                                              |
                                        Hard Stop: report the problem, render nothing
```

The pipeline follows a **Hard Stop** methodology:

1. **The Gatekeeper.** Every download goes through the Tick Inspector before any calculation runs.
2. **The Health Check.** If the inspector finds corrupted data, the pipeline stops and shows the user exactly which rows or dates are affected. This prevents bad data from producing misleading numbers.
3. **The Render.** If the data passes, the analytics are computed and the dashboard is drawn.

Missing calendar dates are treated differently from corrupted values. A small number of gaps produces a visible warning, but the analysis still runs. See the next section for the details.

---

## Methodology

All calculations are performed with pandas and NumPy on the daily closing price unless stated otherwise. Because crypto markets trade every day of the year, annualization uses **365** periods per year (not the 252 used for equities).

### 1. Data source

- **Provider:** Yahoo Finance, accessed through the `yfinance` library.
- **Frequency:** daily bars.
- **Price adjustment:** `auto_adjust=True` is set explicitly so the output does not depend on a library default. For crypto there are no splits or dividends, so adjusted and raw prices are effectively the same.
- **Date range:** the date pickers are limited to the earliest and latest dates Yahoo Finance has for the selected asset. Yahoo treats the end date of a download as exclusive, so the app adds one day to the selected end date, which makes the selected end date inclusive.
- **Column standardization:** columns are lower-cased (`open`, `high`, `low`, `close`, `volume`) and the index is named `date`.

### 2. Data integrity checks (Tick Inspector)

Before any analysis, the downloaded data is audited for the following:

| Check | What it looks for | Result if it fails |
|---|---|---|
| Duplicate rows | Repeated timestamps in the index | **Hard stop** |
| Corrupted high/low | Rows where `low > high` | **Hard stop** |
| Corrupted high vs. open/close | Rows where `open > high` or `close > high` | **Hard stop** |
| Negative volume | Rows where `volume < 0` | **Hard stop** |
| Missing dates | Calendar days between the first and last date that are absent from the data | **Warning** up to a limit, **hard stop** above it |

**Missing dates tolerance.** A full daily calendar is built between the first and last date in the data, and the dates missing from the downloaded index are counted. Up to `MAX_MISSING_DATES` (currently **5**) missing dates are allowed: the analysis runs, and a warning lists the missing dates above the dashboard. Above that limit, the analysis stops and the dates are shown.

**Why a gap matters.** Returns are computed row to row. The row after a gap therefore contains a multi-day move that is treated as a one-day return. This has a negligible effect on cumulative return (the compounding still reaches the correct final price), but it can slightly affect rolling volatility and the returns distribution. That is why the warning mentions those figures specifically.

### 3. Return calculations

Two kinds of daily return are computed from the closing price $P_t$:

**Simple (percentage) return**

$$r_t = \frac{P_t}{P_{t-1}} - 1$$

**Log return**

$$\ell_t = \ln\left(\frac{P_t}{P_{t-1}}\right)$$

- Simple returns are used for **cumulative return** and **drawdown**, because they compound directly into portfolio value.
- Log returns are used for **volatility**, **skewness**, **excess kurtosis**, and the **histogram**. Log returns are the standard choice for statistical work, and at daily frequency they are very close to simple returns.
- The first row of each series is empty (there is no previous day) and is excluded from the statistics.

### 4. Moving averages

Simple moving averages (SMAs) of the close:

$$\text{SMA}_n(t) = \frac{1}{n}\sum_{i=0}^{n-1} P_{t-i}$$

- **20-day SMA** and **50-day SMA** are overlaid on the candlestick chart.
- The SMAs only start once enough history exists, so the 20-day line begins after 20 observations and the 50-day line after 50.

### 5. Rolling volatility

$$\sigma_{\text{annualized}}(t) = \text{std}\left(\ell_{t-29}, \ldots, \ell_t\right) \times \sqrt{365}$$

- The standard deviation of **daily log returns over a rolling 30-day window**, scaled by $\sqrt{365}$ to express it as an annual figure.
- The $\sqrt{365}$ scaling assumes returns are independent from day to day. It is the conventional approximation, not an exact measurement.
- Volatility is a measure of risk: how widely returns have been spread recently.
- The line begins after the first 30 return observations.

### 6. Cumulative return

$$R_{\text{cum}}(t) = \prod_{s=1}^{t}\left(1 + r_s\right) - 1$$

The total percentage gain or loss since the **start of the selected period** (the first close in the range). A value of 1.5 means +150%.

### 7. Drawdown and maximum drawdown

A growth index is built by compounding the daily simple returns, starting at 1:

$$W_t = \prod_{s=1}^{t}\left(1 + r_s\right), \qquad W_0 = 1$$

The running peak and the drawdown are then:

$$M_t = \max_{s \le t} W_s, \qquad D_t = \frac{W_t - M_t}{M_t}$$

- **Drawdown** $D_t$ is how far the asset sits below its highest point so far, as a percentage. It is always zero or negative.
- **Maximum drawdown** is the lowest value of $D_t$ over the selected period: the worst peak-to-trough loss an investor holding for the whole period would have experienced.
- The peak starts at the first close in the range, so a drawdown is measured relative to the start of the selected period if the price immediately falls.
- On the chart, drawdown is drawn as a filled "underwater" area.

### 8. Distribution statistics: skewness and excess kurtosis

Both are computed on **daily log returns** with the pandas estimators `.skew()` and `.kurt()`.

- **Skewness** measures asymmetry. Negative skew means the left tail (large losses) is longer than the right tail. Positive skew means large gains are the more extreme tail.
- **Excess kurtosis** measures tail weight relative to a normal distribution. Pandas `.kurt()` returns *excess* kurtosis (kurtosis minus 3), so a normal distribution scores **0**. Large positive values indicate "fat tails": extreme moves occur far more often than a normal distribution would predict. Crypto assets typically score high.

Also shown on the tape:

- **Average daily log return:** the mean of the daily log returns.
- **Average daily return:** the mean of the daily simple returns.

These are arithmetic daily averages. They are not annualized and should not be read as an expected future return.

### 9. Returns histogram

- Daily log returns are grouped into **fixed-width bins of 0.5%**, so bars always represent the same width regardless of how extreme the data is.
- The x-axis is **zoomed to the 1st to 99th percentile** of returns so the bulk of the distribution is readable. Extreme days are still in the data. Zoom out on the chart to see them.
- Hovering over a bar shows the return range and the number of days that fell in it.

---

## Dashboard layout

- **Sidebar (Configuration):** asset selector, start date, end date, and the Run analysis button.
- **Metrics tape:** skewness, excess kurtosis, average daily log return, average daily return, and maximum drawdown.
- **Charts:**
  - **Risk vs. cumulative return:** cumulative return and annualized rolling volatility.
  - **Drawdown:** the underwater chart for the selected period.
  - **Price action:** candlesticks with the 20-day and 50-day SMAs.
  - **Historical returns:** the returns histogram.

All charts are interactive Plotly figures: hover, zoom, and pan.

---

## Engineering notes

- **Pure functions.** The downloader, inspector, analyzer, and chart builders take DataFrames in and return values out. They contain no `input()` or `print()` calls. Only the Streamlit layer handles user interaction.
- **Caching.** Downloads are cached with `st.cache_data` (one hour for price data, 24 hours for the available date range) so interacting with the app does not repeatedly hit Yahoo Finance. The cache is shared across users.
- **Failures are never cached.** The data functions raise exceptions on failure instead of returning empty results, because Streamlit does not cache exceptions. A temporary Yahoo outage therefore cannot be stored and served to other users.
- **Session state.** The latest result is stored in `st.session_state`, so the dashboard stays on screen when you touch a widget after running an analysis. The dashboard always shows the asset and dates that were actually analyzed, not whatever the widgets currently say.
- **Input validation.** The app checks for a missing ticker, unavailable dates, and a start date that is not before the end date before it downloads anything.
- **Error handling.** Known failures (such as no data for a range) show a specific message. Unexpected failures (such as network errors) show a generic, user-friendly message instead of a traceback.

---

## Limitations and caveats

- **Data quality depends on Yahoo Finance.** It is a free, aggregated source. It can have gaps, delayed updates, or occasional errors, and its data differs from exchange-level data. The inspector catches structural problems, not every possible inaccuracy.
- **Newer and smaller assets have short histories.** Statistics such as skewness, kurtosis, and volatility are unreliable over short windows. Very short ranges can also leave the SMAs and rolling volatility empty.
- **Stablecoins and wrapped assets** (USDT, WETH) behave differently from freely floating assets. A stablecoin's near-zero returns and extreme kurtosis reflect its peg, not typical market behavior.
- **Annualization is an approximation.** The $\sqrt{365}$ scaling assumes independent daily returns.
- **Gaps affect returns.** If a date is missing, the following return spans multiple days. See the Tick Inspector section.
- **Historical results are not predictive.** All figures describe the past.
- **No transaction costs, slippage, or taxes** are modeled anywhere in the app.

---

## Running locally

```bash
git clone https://github.com/priyanshsx/kwant-terminal
cd kwant-terminal

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
streamlit run app.py
```

Core dependencies: `streamlit`, `pandas`, `numpy`, `plotly`, `yfinance`. Versions are pinned in `requirements.txt` so that a library update, especially in `yfinance`, cannot silently change behavior.

---

## Project history

The app grew in four phases:

1. **OHLCV Downloader.** A command-line tool that queried Yahoo Finance, standardized the column names, and saved raw data to CSV.
2. **Tick Inspector.** Added data-cleaning checks (duplicates, missing dates, negative volume, corrupted price ticks) that run before any analysis.
3. **Quant Analyzer.** Added returns, SMAs, rolling volatility, cumulative return, and maximum drawdown.
4. **Web integration.** Refactored the three scripts into pure functions that pass data between them in memory as DataFrames, and added the Streamlit interface and Plotly dashboard.

---

## Roadmap

Planned, not yet implemented:

- Sharpe and Sortino ratios
- CAGR
- Strategy backtesting (signal generation, a backtest engine with transaction costs, and a buy-and-hold benchmark)
- Benchmark comparison against other asset classes (gold, oil, equities)
- Always-on hosting on a custom domain

---

## Feedback

Found a bug or have a feature request? Open an issue on the repository.
