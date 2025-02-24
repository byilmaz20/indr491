import pandas as pd
import holidays

# Create a date range for historical data
date_range = pd.date_range(start="2025-03-29", end="2025-12-31", freq="D")
df = pd.DataFrame(date_range, columns=["date"])

# Define country-specific holidays
country_holidays = holidays.TR()  # Change to your relevant country

# Convert df["date"] to datetime.date for comparison
df["date"] = df["date"].dt.date

# Create a holiday indicator
df["is_holiday"] = df["date"].apply(lambda x: x in country_holidays).astype(int)

# Extract holiday names (optional for categorical features)
df["holiday_name"] = df["date"].apply(lambda x: country_holidays.get(x) if x in country_holidays else "None")

# Rolling window for holiday influence (e.g., 3 days before and after)
"""df["days_to_next_holiday"] = df["date"].apply(lambda x: min([(h - x).days for h in country_holidays if h > x] or [30]))
df["days_since_last_holiday"] = df["date"].apply(lambda x: min([(x - h).days for h in country_holidays if h < x] or [30]))
"""

# Print first few rows
print(df)