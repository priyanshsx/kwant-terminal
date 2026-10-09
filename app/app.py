import streamlit as st 
import pandas as pd 
import numpy as np 
import plotly.graph_objects as go 
from plotly.subplots import make_subplots
import yfinance as yf
from datetime import timedelta

# ========================================================================================= #

# global variables 

# list of available assets you can download historical data for from yfinance
available_assets = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'HYPE-USD', 'USDT-USD', 'BNB-USD', 'XRP-USD',
    'ZEC-USD', 'WETH-USD', 'TRX-USD', 'NEAR-USD', 'LSK-USD']

MAX_MISSING_DATES = 5

# checking min and max for date 
@st.cache_data(ttl=86400)

def get_crypto_date_bounds(symbol):
    ticker = yf.Ticker(symbol)
    df = ticker.history(period='max')

    if df.empty: 
        raise ValueError("No history available for this asset.") 

    return df.index.min().date(), df.index.max().date()

# OHLCV downloader 
# the function download_data(ticker) should effectively download the raw csv data 
# it needs to be stripped off of input() and print() for it to work flawlessly 
# caching data 

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

# tick inspector: checks for corrupted highs and lows, negative volume, and high, open, close

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

# quant_analyzer  

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
    max_drawdown = df['drawdown'].min()

    # visualizations 
    fig = go.Figure()

    # adding the candlestick trace 

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='Price'
    ))

    # adding the sma traces 

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['sma_20'],
        mode='lines',
        name='20-day SMA',
        line=dict(color='blue', width=1.5)
    ))

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['sma_50'],
        mode='lines',
        name='50-day SMA',
        line=dict(color='orange', width=1.5)
    ))

    # making subplots for quant charts 

    quant_fig = make_subplots(rows=3, cols=1, shared_xaxes=True)

    # risk vs. return 

    quant_fig.add_trace(go.Scatter(
        x=df.index,
        y=df['cumulative_return'],
        mode='lines',
        name='Return',
        line=dict(color='green', width=1.5)
    ), row=1, col=1)

    quant_fig.add_trace(go.Scatter(
        x=df.index,
        y=df['rolling_vol_annualized'],
        mode='lines',
        name='Annualized Risk',
        line=dict(color='purple', width=1.5)
    ), row=2, col=1)

    # underwater drawdown chart 

    quant_fig.add_trace(go.Scatter(
        x=df.index,
        y=df['drawdown'],
        mode='lines',
        name='Drawdown',
        line=dict(color='red', width=1.5),
        fill='tozeroy'
    ), row=3, col=1)

    # returns distribution histogram 

    hist_fig = go.Figure(go.Histogram(x=df['log_returns'].dropna(), nbinsx=100, name='Returns Distribution'))

    return fig, quant_fig, hist_fig

# user interface 

st.title("Kwant Terminal: Quantitative Analysis for Crypto Assets")

# managing the sidebar 

st.sidebar.header("Configuration")

# step 1: request for ticker and dates
ui_ticker = st.sidebar.selectbox(label='select a ticker from the list',
                         options=available_assets, 
                         index=None)

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
                                            value=min_date,
                                            min_value=min_date,
                                            max_value=max_date)

        ui_end_date = st.sidebar.date_input(label='select end date',
                                            value=max_date,
                                            min_value=min_date,
                                            max_value=max_date)
else:
    st.sidebar.info("Please select a ticker above to configure dates.")
    ui_start_date, ui_end_date = None, None

# letting the user click the run analysis button to continue
if st.sidebar.button("Run analysis"):

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

    st.success(f"Data successfully downloaded! \nNow inspecting and generating a data health report.")

    # step 2: clean data (if healthy)
    health_report = tick_inspector(raw_data_df)

    if health_report['is_healthy'] == True:
        st.success("Data is clean. Analysis initiated.")

        missing = health_report['missing_dates']
        if len(missing) > 0:
            date_list = ", ".join(missing.strftime('%Y-%m-%d'))
            st.warning(f"{len(missing)} date(s) missing from the source data: {date_list}. "
                       f"The analysis still ran, but volatility and return distribution figures may be slightly affected.")

        # calling the quant_analyzer function 
        fig, quant_fig, hist_fig = quant_analyzer(raw_data_df, ui_ticker)

        # building the charts 
        st.subheader(f"{ui_ticker} Price Action")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader(f"{ui_ticker} Quant Analysis")
        st.plotly_chart(quant_fig, use_container_width=True)

        st.subheader(f"{ui_ticker} Historical Returns")
        st.plotly_chart(hist_fig, use_container_width=True)
        
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

