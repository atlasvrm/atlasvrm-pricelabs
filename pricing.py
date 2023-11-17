import pandas as pd
from utilities.pricelabs_utils import get_airbnb_title
from tqdm import tqdm

# Load the CSV data into a pandas DataFrame
comps_df = pd.read_csv("data/ListingComps.csv")
trends_df = pd.read_csv("data/MarketTrends.csv")

# Convert 'Star Rating' to numeric and set errors='coerce'
comps_df["Star Rating"] = pd.to_numeric(comps_df["Star Rating"], errors="coerce")
comps_df = comps_df.dropna(subset=["Star Rating"])

# Remove rows where "Star Rating" equals "#NAME?" (as in your previous requirement)
comps_df = comps_df[comps_df["Star Rating"] != "#NAME?"]


# Apply the filters to the DataFrame
MIN_RATING = 4.5
MIN_REVIEWS = 10
MIN_REVENUE = 10000
MIN_OCCUPANCY = 30
MIN_ACTIVE_NIGHTS = 180

comps_filtered = comps_df[
    (comps_df["Star Rating"] >= MIN_RATING)
    & (comps_df["Reviews"] >= MIN_REVIEWS)
    & (comps_df["Revenue"] >= MIN_REVENUE)
    & (comps_df["Occupancy"] >= MIN_OCCUPANCY)
    & (comps_df["Active Nights"] >= MIN_ACTIVE_NIGHTS)
]

# Sort the DataFrame by 'Revenue' in descending order
comps_filtered = comps_filtered.sort_values(by="Revenue", ascending=False)

# Get the Airbnb titles for each listing
tqdm.pandas(desc="Fetching Titles", bar_format="\033[94;1m{l_bar}{bar}|\033[0m")
comps_filtered["Listing Title"] = comps_filtered["Link"].progress_apply(
    get_airbnb_title
)

# Filter out rows with 'Listing Title' = 'N/A'
comps_filtered = comps_filtered[comps_filtered["Listing Title"] != "N/A"]
comps_filtered.to_csv("data/CompsFiltered.csv", index=False, mode="w")

bedroom_dataframes = {}

# Iterate over each unique value in the 'Bedroom' column
for n in comps_df["Bedrooms"].unique():
    # Filter the DataFrame and store it in the dictionary
    bedroom_dataframes[n] = comps_df[comps_df["Bedrooms"] <= n].sort_values(
        by="Revenue", ascending=False
    )
