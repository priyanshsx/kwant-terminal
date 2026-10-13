import pandas as pd 

# this file audits the download csv data from yahoo finance and checks it for any errors 

# asking the user for the file they want read 

while True:
    user_file = input("Please enter the name of the file you want the Tick Inspector to read: ")

    try: 
       df = pd.read_csv(user_file, index_col='date', parse_dates=True)
       break
    except FileNotFoundError:
       print(f"\nFile not found. Please ensure that the file is in the folder where this script runs from and ensure that you get the name exactly right.\n")

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

# printing data health report 
print(f"\n==========  Printing Data Health Report  ==========\n")
print(f"Duplicate rows found: {duplicates}")
print(f"Missing days found (if any): {len(missing_dates)}")
print(f"Corrupted highs and lows found (if any): {len(corrupted_high_low)}")
print(f"Negative volume (if any): {len(negative_volume)}")
print(f"Rows where open or close > high of that day (if any): {len(high_open_close)}")
print(f"\n==========  End of report  ==========\n")

if len(missing_dates) > 0:
   print(f"The missing dates are: {missing_dates}") 
if len(corrupted_high_low) > 0:
   print(f"The corrupted highs and lows are: {corrupted_high_low}")
if len(negative_volume) > 0:
   print(f"The negative volume rows are: {negative_volume}")
if len(high_open_close) > 0:
   print(f"The rows where high is less than open or close for the day are: {high_open_close}")