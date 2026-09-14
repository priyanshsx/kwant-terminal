import streamlit as st 
import pandas as pd 
import numpy as np 
import plotly.graph_objects as go 
from plotly.subplots import make_subplots
import yfinance as yf

# ========================================================================================= #

# global variables 

# list of available assets you can download historical data for from yfinance
available_assets = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'HYPE-USD', 'USDT-USD', 'BNB-USD', 'XRP-USD',
    'ZEC-USD', 'WETH-USD', 'TRX-USD', 'NEAR-USD', 'LSK-USD']

# OHLCV downloader 
# the function download_data(ticker) should effectively download the raw csv data 
# it needs to be stripped off of input() and print() for it to work flawlessly 
def fetch_asset(ui_ticker, ui_start_date, ui_end_date):

    # downloads the raw data 
    asset = yf.download(ticker=ui_ticker, start=ui_start_date, end=ui_end_date)

    # handles if yf.download did not work/failed 
    if asset.empty:
        return None
    else:
        # formats the columns into a standard from the raw downloaded data   
        asset.columns = asset.columns.droplevel(1).str.lower()
        asset.index.name = 'date'
        asset.columns.name = None 
    return asset 




# tick inspector 
# in this case the tick_inspector function should do exactly the same as above 




# quant_analyzer should do same as above 



# user interface 
# build a control panel on the left side of the screen 
# here the user should be able to type their ticker or ideally choose from a dropdown menu 
# execution should happen based on checking if st.sidebar.button 


st.title("Kwant Terminal")

# managing the sidebar 

st.sidebar.head("Configuration")

# step 1: request for ticker and dates
ui_ticker = st.sidebar.selectbox(label='select ticker from the list',
                         options=available_assets, 
                         index=None)
ui_start_date = st.sidebar.date_input(label='select start date',
                              value=None,
                              min_value=None,
                              max_value="today")
ui_end_date = st.sidebar.date_input(label='select end date',
                              value="today",
                              min_value=None,
                              max_value="today")

# letting the user click the run analysis button to continue
if st.sidebar.button("Run analysis"):

    # checking if a ticker was selected
    if ui_ticker is None:
        st.error(f"Please select a valid ticker before running the analysis.")
    else:
        # attemps to download the data 
        with st.spinner(f"Downloading {ui_ticker} data..."):
            raw_data = fetch_asset(ui_ticker, ui_start_date, ui_end_date)

        # if no data available 
        if raw_data is None:
            st.error("Yahoo Finance failed to return data. Please check your dates and try again.")
        else:
            st.success(f"Data successfully downloaded!")
            st.dataframe(raw_data.head()) # why do we need this? 

# step 2: clean data 
