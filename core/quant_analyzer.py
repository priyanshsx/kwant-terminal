import pandas as pd 
import numpy as np 
import plotly.graph_objects as go 
from plotly.subplots import make_subplots

# importing the raw csv file and creating a df from it 

while True:
    user_file = input(f"Please enter the name of the file you'd like to run the Quantitative Analysis Pack on: ")

    try:
        df = pd.read_csv(user_file, index_col='date', parse_dates=True)
        break
    except FileNotFoundError:
        print(f"\nFile not found. Please ensure that the file is in the folder where this script runs from and ensure that you get the name exactly right.\n")

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

# saving the processed data as a new csv file 
df.to_csv('/home/priyansh/Documents/d/basic_quant_pack/processed/processed_data.csv')

# print info 
print(df.info())

# saving the processed file 
print(f"\nThe file is now saved as processed_data.csv in the folder: processed.")

# visualization engine (concept to research: plotly candlestick charts)

# creating the empty canvas 

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

# updating the final layout 

filename = user_file.replace(".csv", "")

fig.update_layout(
    title=f'{filename} Analysis',
    xaxis_title='Date',
    yaxis_title='Price (USD)'
)

# making subplots for quant charts 

quant_fig = make_subplots(rows=3, cols=1, shared_xaxes=True)

# risk vs. return 

quant_fig.add_trace(go.Scatter(
    x=df.index,
    y=df['cumulative_return'],
    mode='lines',
    name='return',
    line=dict(color='green', width=1.5)
), row=1, col=1)

quant_fig.add_trace(go.Scatter(
    x=df.index,
    y=df['rolling_vol_annualized'],
    mode='lines',
    name='annualized risk',
    line=dict(color='purple', width=1.5)
), row=2, col=1)

# underwater drawdown chart 

quant_fig.add_trace(go.Scatter(
    x=df.index,
    y=df['drawdown'],
    mode='lines',
    name='drawdown',
    line=dict(color='red', width=1.5),
    fill='tozeroy'
), row=3, col=1)

# returns distribution histogram 

hist_fig = go.Figure(go.Histogram(x=df['log_returns'].dropna(), nbinsx=100, name='Returns Distribution'))

# adding chart titles 

quant_fig.update_layout(title=f"{filename} Quant Sheet")
hist_fig.update_layout(title=f"{filename} Historical Distribution")

# printing the charts

fig.show()
quant_fig.show()
hist_fig.show()