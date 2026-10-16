#---------------------beginning-of-code------------------------#

# importing libraries
import streamlit as st 
import pandas as pd 
import numpy as np 
import plotly.graph_objects as go 
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import timedelta
from pathlib import Path
st.set_page_config(layout="wide")
ASSETS = Path(__file__).parent/"assets"
st.logo(str(ASSETS / "logo-mark-256.png"), link="https://quartermasterlabs.com")
#--------------------------------------------------------------#

# Global Variables 

# list of available assets you can download historical data for from yfinance
available_assets = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'HYPE-USD', 'USDT-USD', 'BNB-USD', 'XRP-USD',
    'ZEC-USD', 'WETH-USD', 'TRX-USD', 'NEAR-USD', 'LSK-USD']

MAX_MISSING_DATES = 5
#--------------------------------------------------------------#

# Checks for date ranges for which data is available from yfinance
@st.cache_data(ttl=86400)

def get_crypto_date_bounds(symbol):
    ticker = yf.Ticker(symbol)
    df = ticker.history(period='max')

    if df.empty: 
        raise ValueError("No history available for this asset.") 

    return df.index.min().date(), df.index.max().date()
#--------------------------------------------------------------#

# OHLCV downloader: downloads the raw data from yfinance
@st.cache_data(ttl=3600, max_entries=100)

def fetch_asset(ui_ticker, ui_start_date, ui_end_date):

    # downloads the raw data 
    asset = yf.download(ui_ticker, start=ui_start_date, end=ui_end_date, auto_adjust=True, progress=False)

    # handles if yf.download did not work/failed 
    if asset.empty:
        raise ValueError("No data found for this ticker and date range.")

    # formats the columns into a standard from the raw downloaded data   
    asset.columns = asset.columns.droplevel(1).str.lower()
    asset.index.name = 'date'
    asset.columns.name = None 
    return asset 
#--------------------------------------------------------------#

# Tick Inspector: checks for corrupted highs and lows, negative volume, and high, open, close
def tick_inspector(df):
    # checking for duplicates 
    duplicates = df.index.duplicated().sum()

    # checking for missing dates 
    calendar = pd.date_range(start=df.index.min(), end=df.index.max())
    missing_dates = calendar.difference(df.index)

    # checking for corrupted highs and lows where low > high 
    corrupted_high_low = df[df['low'] > df['high']]

    # checking for where volume is below 0 
    negative_volume = df[df['volume'] < 0]

    # checking for where high vs. open/close check 
    high_open_close = df[(df['open'] > df['high']) | (df['close'] > df['high'])]

    # doing a global boolean mask check for bad data 
    is_healthy = len(missing_dates) <= MAX_MISSING_DATES and len(corrupted_high_low) == 0 and len(negative_volume) == 0 and len(high_open_close) == 0 and duplicates == 0

    return{"is_healthy": is_healthy, 
           "duplicates": duplicates,
           "missing_dates": missing_dates,
           "corrupted_high_low": corrupted_high_low,
           "negative_volume": negative_volume,
           "high_open_close": high_open_close}
#--------------------------------------------------------------#

# Quant Analyzer: computes the metrics for the charts 
def quant_analyzer(df, ui_ticker):
    # daily returns 
    df['daily_returns'] = df['close'].pct_change()

    # moving averages
    df['sma_20'] = df['close'].rolling(window=20).mean()
    df['sma_50'] = df['close'].rolling(window=50).mean()

    # calculating the log returns  
    df['log_returns'] = np.log(df['close'] / df['close'].shift(1)) 

    # rolling volatility for a 30-day period (annualized, for 365 trading days for crypto)
    df['rolling_vol_annualized'] = df['log_returns'].rolling(window=30).std() * np.sqrt(365)

    # calculating the cumulative return 
    df['cumulative_return'] = (1 + df['daily_returns']).cumprod() - 1 

    # calculating the max drawdown 
    df['cum_return_for_drawdown'] = (1 + df['daily_returns'].fillna(0)).cumprod()
    df['running_max'] = df['cum_return_for_drawdown'].cummax()
    df['drawdown'] = ((df['cum_return_for_drawdown'] - df['running_max']) / df['running_max'])
    df['max_drawdown'] = df['drawdown'].min()

    # calculating the tape metrics: skew, kurtosis, sharpe, sortino 
    df['skewness'] = df['log_returns'].skew()
    df['kurtosis'] = df['log_returns'].kurt()
    df['avg_daily_log_return'] = df['log_returns'].mean()
    df['avg_daily_simple_return'] = df['daily_returns'].mean()

    return df
#--------------------------------------------------------------#

# Percent Format Function for low-volatility assets 
def pct_format(span):
    if span >= 0.10:
        return ".0%"
    if span >= 0.01:
        return ".1%"
    if span >= 0.001:
        return ".2%"
    return ".3%"

#--------------------------------------------------------------#

# Styling function for all the figures 
def style_fig(fig, height=380):
    fig.update_layout(
        height=height,
        margin=dict(t=40, b=30, l=50, r=20),
        legend=dict(orientation="h", y=1.12),
        template="plotly_dark",
        paper_bgcolor="#101010", plot_bgcolor="#101010",
        font=dict(family="Inter, sans-serif", color="#9498A0", size=12),
    )

    fig.update_xaxes(gridcolor="#1e1e1e")
    fig.update_yaxes(gridcolor="#1e1e1e")
    
    return fig
#--------------------------------------------------------------#

# Visualisation Function: builds the charts for the metrics computed above 
def visualize(df):

    # Global variables for function 
    log_rets = df['log_returns'].dropna()
    lo = log_rets.quantile(0.01)
    hi = log_rets.quantile(0.99)
    span = hi - lo 
    bin_size = span / 50 if span > 0 else 0.001
    ret_fmt = pct_format(span)

    cum_ret = df['cumulative_return'].dropna()
    vol = df['rolling_vol_annualized'].dropna()

    cum_fmt = pct_format(cum_ret.max() - cum_ret.min()) if len(cum_ret) else ".1%"
    vol_fmt = pct_format(vol.max() - vol.min()) if len(vol) else ".1%"

    # visualizations 
    candlestick_fig = go.Figure()

    # adding the candlestick trace 
    candlestick_fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='Price'
    ))

    # adding the sma traces 
    # sma 20
    candlestick_fig.add_trace(go.Scatter(
        x=df.index,
        y=df['sma_20'],
        mode='lines',
        name='20-day SMA',
        line=dict(color='#60A5FA', width=1.5)
    ))

    # sma 50
    candlestick_fig.add_trace(go.Scatter(
        x=df.index,
        y=df['sma_50'],
        mode='lines',
        name='50-day SMA',
        line=dict(color='#FBBF24', width=1.5)
    ))

    candlestick_fig.update_layout(xaxis_rangeslider_visible=False)

    # making subplots for quant charts 
    risk_vs_cum_return_fig = make_subplots(specs=[[{"secondary_y": True}]])

    # risk vs. return 
    risk_vs_cum_return_fig.add_trace(go.Scatter(
        x=df.index,
        y=df['cumulative_return'],
        mode='lines',
        name='Return',
        line=dict(color='#34D399', width=1.5)
    ), secondary_y=False)

    risk_vs_cum_return_fig.add_trace(go.Scatter(
        x=df.index,
        y=df['rolling_vol_annualized'],
        mode='lines',
        name='Annualized Risk',
        line=dict(color='#A78BFA', width=1.5)
    ), secondary_y=True)

    # underwater drawdown chart 
    drawdown_fig = go.Figure()
    drawdown_fig.add_trace(go.Scatter(
        x=df.index,
        y=df['drawdown'],
        mode='lines',
        name='Drawdown',
        line=dict(color='#EF4444', width=1.5),
        fill='tozeroy'
    ))

    drawdown_fig.update_yaxes(title_text="Drawdown", tickformat=pct_format(abs(df['drawdown'].min())))

    # returns distribution histogram 
    returns_histogram_fig = go.Figure(go.Histogram(
    x=log_rets,
    xbins=dict(size=bin_size),
    name='Returns Distribution',
    marker_color="#60A5FA",
    hovertemplate=f"Daily return near %{{x:{ret_fmt}}}<br>Days: %{{y}}<extra></extra>"
    ))

    risk_vs_cum_return_fig.update_yaxes(
    title_text="Cumulative Return",
    tickformat=cum_fmt,
    title_font_color="#34D399",
    secondary_y=False)

    risk_vs_cum_return_fig.update_yaxes(
    title_text="Annualized Volatility",
    tickformat=vol_fmt,
    title_font_color="#A78BFA",
    secondary_y=True)

    returns_histogram_fig.update_xaxes(range=[lo, hi], 
                          title_text="Daily log returns",
                          tickformat=ret_fmt)
    returns_histogram_fig.update_yaxes(title_text="Number of days")

    return (
        style_fig(candlestick_fig), 
        style_fig(risk_vs_cum_return_fig), 
        style_fig(drawdown_fig), 
        style_fig(returns_histogram_fig)
    )
#--------------------------------------------------------------#

# User Interface 

# managing the sidebar 
st.sidebar.header("Configuration")

# Step 1: request for ticker and dates
ui_ticker = st.sidebar.selectbox(label='select a ticker from the list',
                         options=available_assets, 
                         index=None)

# managing ticker entries
if ui_ticker:
    try: 
        min_date, max_date = get_crypto_date_bounds(ui_ticker)
    except ValueError:
        st.sidebar.warning("No history is available for this asset. Please try another asset.")
        ui_start_date, ui_end_date = None, None 
    except Exception: 
        st.sidebar.warning("Couldn't reach Yahoo Finance. Please try again in a minute.")
        ui_start_date, ui_end_date = None, None 
    else:   
        st.sidebar.info(f"Available from {min_date} to {max_date}")

        ui_start_date = st.sidebar.date_input(label='select start date',
                                            value=max(min_date, (max_date - timedelta(days=365))),
                                            min_value=min_date,
                                            max_value=max_date)

        ui_end_date = st.sidebar.date_input(label='select end date',
                                            value=max_date,
                                            min_value=min_date,
                                            max_value=max_date)
else:
    st.sidebar.info("Please select a ticker above to configure dates.")
    ui_start_date, ui_end_date = None, None
#--------------------------------------------------------------#

# letting the user click the run analysis button to continue
if st.sidebar.button("Run analysis", type="primary"):
    st.session_state.pop("result", None)

    # input validation 
    if ui_ticker is None:
        st.error("Please select a ticker before running the analysis.")
        st.stop()
    if ui_start_date is None or ui_end_date is None:
        st.error("Date range unavailable for this asset. Please try another ticker.")
        st.stop()

    if ui_start_date >= ui_end_date:
        st.error("Start date must be before the end date.")
        st.stop()

    # data download
    try: 
        with st.spinner(f"Downloading {ui_ticker} data..."):
            raw_data_df = fetch_asset(ui_ticker, ui_start_date, ui_end_date + timedelta(days=1)) 
    except ValueError as e:
        st.error(str(e))
        st.stop()
    except Exception:
        st.error("Couldn't reach Yahoo Finance. Please try again in a minute.")
        st.stop()
#--------------------------------------------------------------#

    # Step 2: Clean data (if healthy)
    health_report = tick_inspector(raw_data_df)

    if health_report['is_healthy'] == True:
        enriched_data = quant_analyzer(raw_data_df,ui_ticker)
    else:
        enriched_data = None
    
    # storing the session state 
    st.session_state["result"] = {
            "ticker": ui_ticker,
            "start_date": ui_start_date,
            "end_date": ui_end_date,
            "health_report": health_report,
            "enriched_data": enriched_data
        }
    st.toast("Inspection complete.")

result = st.session_state.get("result")

if result:
    st.title(f"Visualized quant metrics for {result['ticker']}")
    health_report = result["health_report"]

    if health_report["is_healthy"]:
        enriched_data = result["enriched_data"] 

        missing = health_report['missing_dates']
        if len(missing) > 0:
            date_list = ", ".join(missing.strftime('%Y-%m-%d'))
            st.warning(f"{len(missing)} date(s) missing from the source data: {date_list}. "
                       f"The analysis still ran, but volatility and return distribution figures may be slightly affected.")

        # visualizing charts
        charts = visualize(enriched_data)
        candlestick_fig, risk_vs_cum_return_fig, drawdown_fig, returns_histogram_fig = charts

        # Building the columns in streamlit 
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric(label="Skewness", value=round(enriched_data['skewness'].iloc[-1], 4))
        m2.metric(label='Excess Kurtosis', value=round(enriched_data['kurtosis'].iloc[-1], 4))
        m3.metric(label='Avg. Daily Log Return', value=f"{enriched_data['avg_daily_log_return'].iloc[-1]: .2%}")
        m4.metric(label='Avg. Daily Return', value=f"{enriched_data['avg_daily_simple_return'].iloc[-1]: .2%}")
        m5.metric(label="Max Drawdown",value=f"{enriched_data['max_drawdown'].iloc[-1]: .2%}")

        # Step 3: Build the charts  
        top_left, top_right = st.columns(2, gap="medium")

        with top_left:
            st.subheader(f"{result['ticker']} Risk vs. Return")
            st.plotly_chart(risk_vs_cum_return_fig, use_container_width=True)

        with top_right:
            st.subheader(f"{result['ticker']} Price Action with SMAs")
            st.plotly_chart(candlestick_fig, use_container_width=True)

        bottom_left, bottom_right = st.columns(2, gap="medium")

        with bottom_left:
            st.subheader(f"{result['ticker']} Drawdown")
            st.plotly_chart(drawdown_fig, use_container_width=True)

        with bottom_right:
            st.subheader(f"{result['ticker']} Historical Returns")
            st.plotly_chart(returns_histogram_fig, use_container_width=True)
            st.caption("Each bar groups days by their return. Hover to see the return range "
                       "and how many days fell in it. Axis zoomed to the 1st-99th percentile.")
#--------------------------------------------------------------#

# Dealing with bad data         
    else:
        st.error("Found bad data. Analysis stopped.")

        if health_report['duplicates'] > 0:
            st.warning(f"Found {health_report['duplicates']} duplicate rows.")

        if len(health_report['negative_volume']) > 0:
            st.warning("Negative volume ticks found: ")
            st.dataframe(health_report['negative_volume'])

        if len(health_report['missing_dates']) > MAX_MISSING_DATES:
            missing = health_report['missing_dates']
            date_list = ", ".join(missing[:10].strftime('%Y-%m-%d'))
            st.warning(f"Found {len(health_report['missing_dates'])} missing dates which exceed the allowed missing dates value of {MAX_MISSING_DATES}. Missing: {date_list}.")

        if len(health_report['corrupted_high_low']) > 0:
            st.warning("Rows where low is higher than high: ")
            st.dataframe(health_report['corrupted_high_low'])

        if len(health_report['high_open_close']) > 0:
            st.warning("Rows where open or close is higher than high: ")
            st.dataframe(health_report['high_open_close'])

else:
    # Managing the empty state 

    left, middle, right = st.columns([1, 2, 1])

    with middle:
        st.logo(str(ASSETS / "logo-mark-256.png"), link="https://quartermasterlabs.com")

        st.markdown("# Quantitative risk analysis for crypto assets")
        st.markdown(
            "Pick an asset and a timeframe. Quartermaster audits the data "
            " before it charts anything, then shows what the risk actually "
            " looked like."
        )

        st.markdown(
            "1. **Select a ticker** in the sidebar\n"
            "2. **Choose your timeframe**\n"
            "3. **Run analysis**"
        )

        st.image(str(ASSETS/"sample-dashboard.png"))
        st.caption("Example: BTC-USD over the last year.")

        st.markdown("[Read the methodology](https://quartermasterlabs.com/docs)")


#--------------------------------------------------------------#
#----------------------End-of-code-----------------------------#