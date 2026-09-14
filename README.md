# Welcome to Kwant Terminal!

Kwant Terminal helps you source crypto assets, clean raw csv files/data and plot quantitative charts to better visualize trends. What's best? You can decide your own timeframe! 

Kwant Terminal is an institutional-grade, event-driven web application built with Python and Streamlit. It serves as a unified pipeline for quantitative traders to download historical market data, automatically audit data integrity, and visualize advanced risk-adjusted metrics using interactive Plotly dashboards.

## 🚀 The Engineering Journey

This application represents the culmination of three distinct development phases, evolving from isolated terminal scripts into a cohesive full-stack application:

1. **Phase 1: The OHLCV Downloader**
   Started as a local CLI tool to query the Yahoo Finance API, format column headers, and save raw OHLCV (Open, High, Low, Close, Volume) data to local CSV files. 
2. **Phase 2: The Tick Inspector**
   Evolved to introduce institutional data-cleaning practices. Before running any math, this engine audits the data for missing trading days, duplicated indices, negative volumes, and corrupted price ticks (e.g., lows higher than highs).
3. **Phase 3: The Quant Analyzer**
   Introduced advanced financial mathematics, calculating daily log returns, 20/50-day SMAs, rolling annualized volatility (scaled for a 365-day crypto market), and maximum drawdown. 
4. **Phase 4: The Web Integration (Current)**
   Refactored all three scripts into "Pure Functions." Terminal inputs (`input()`) and outputs (`print()`) were stripped away. Data is now passed seamlessly in-memory (RAM) as Pandas DataFrames, orchestrated by a Streamlit graphical user interface.

## 🧠 Core Architecture

The pipeline operates on a strict **Hard Stop** methodology. 
* **The Gatekeeper:** When a user requests an asset, the data is pulled and immediately fed into the Tick Inspector. 
* **The Health Check:** If anomalies are found, the pipeline halts and alerts the user to the corrupted rows, preventing bad data from generating false trading signals.
* **The Render:** If the data passes inspection, the UI renders three interactive Plotly canvases.

## 📊 Visual Analytics Suite

* **Price Action Canvas:** An interactive candlestick chart overlaid with 20-day and 50-day Simple Moving Averages.
* **The Quant Tearsheet:** A 3-story, x-axis-synchronized dashboard comparing Cumulative Return (reward), Rolling Volatility (risk), and a filled underwater chart mapping Maximum Drawdown.
* **Returns Distribution:** A 100-bin histogram of log returns to visualize market behavior and identify unpredictable "fat tail" events.

## 💻 Installation & Usage

1. **Prerequisites:** Ensure you have Python installed.
2. **Install Dependencies:** 
   Run the following command in your terminal:
   `pip install streamlit pandas numpy plotly yfinance`
3. **Launch the App:** 
   Navigate to the directory containing `app.py` and run:
   `streamlit run app.py`
4. **Interface:** The application will automatically open in your default web browser. Use the left-hand sidebar to select an asset ticker and define your date range.