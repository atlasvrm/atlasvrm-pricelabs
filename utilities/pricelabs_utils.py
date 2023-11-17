import geopandas as gpd
import os
from shapely.geometry import Point
import pandas as pd
import requests
from bs4 import BeautifulSoup
import io
import base64
import dash_bootstrap_components as dbc
import aiohttp
import asyncio
from tqdm import tqdm


def spatial_join_with_shp(csv_filepath, shp_filepath, output_filepath):
    """
    Perform a spatial join between a CSV file and a .shp file.

    Parameters:
    - csv_filepath (str): Path to the CSV file.
    - shp_filepath (str): Path to the .shp file.
    - output_filepath (str): Path where the result will be saved as a new CSV.

    Returns:
    None. Writes the result to the specified output file.
    """

    # Read the CSV file
    df = pd.read_csv(csv_filepath)

    # Read the .shp file
    gdf = gpd.read_file(shp_filepath)

    # Create a geometry column in the CSV DataFrame
    df["geometry"] = [Point(xy) for xy in zip(df["lng"], df["lat"])]

    # Convert the CSV DataFrame to a GeoDataFrame
    df = gpd.GeoDataFrame(df, geometry="geometry")
    df.crs = gdf.crs

    # Perform a spatial join between the two GeoDataFrames
    result = gpd.sjoin(df, gdf, predicate="within")

    # Save the result
    result.to_csv(output_filepath, index=False)


async def get_airbnb_title_with_hyperlink(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            content = await response.text()
            soup = BeautifulSoup(content, features="html.parser")
            title_tag = soup.find("meta", property="og:description")
            title = title_tag["content"] if title_tag else "N/A"
            # Return the title and URL in Markdown link format
            return f"[{title}]({url})" if title != "N/A" else "N/A"


async def fetch_all_titles(df):
    tasks = [
        asyncio.create_task(get_airbnb_title_with_hyperlink(url)) for url in df["Link"]
    ]
    hyperlinks = await asyncio.gather(*tasks)
    df["Listing Title"] = hyperlinks
    return df


def parse_contents(contents, filename):
    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)
    try:
        if "csv" in filename:
            # Assume that the user uploaded a CSV file
            return pd.read_csv(io.StringIO(decoded.decode("utf-8")))
    except Exception as e:
        print(e)
        return dbc.Alert("There was an error processing this file.", color="danger")


def process_uploaded_files(
    comps_contents, trends_contents, comps_filename, trends_filename, market_dir
):
    # Save raw files
    raw_comps_path = os.path.join(market_dir, "raw_comps.csv")
    raw_trends_path = os.path.join(market_dir, "raw_trends.csv")
    save_raw_file(comps_contents, raw_comps_path)
    save_raw_file(trends_contents, raw_trends_path)

    # Process files
    comps_df = parse_contents(comps_contents, comps_filename)
    trends_df = parse_contents(trends_contents, trends_filename)

    return comps_df, trends_df


def create_bedroom_dfs(df):
    bedroom_dataframes = {}
    for n in df["Bedrooms"].unique():
        bedroom_dataframes[n] = df[df["Bedrooms"] <= n].sort_values(
            by="Revenue", ascending=False
        )
    return bedroom_dataframes


def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)


def save_raw_file(contents, filepath):
    decoded_contents = base64.b64decode(contents.split(",")[1])
    with open(filepath, "wb") as f:
        f.write(decoded_contents)


def process_comps(
    comps_df, min_rating, min_reviews, min_revenue, min_occupancy, min_active_nights
):
    comps_df["Star Rating"] = pd.to_numeric(comps_df["Star Rating"], errors="coerce")
    comps_df.dropna(subset=["Star Rating"], inplace=True)
    comps_df = comps_df[comps_df["Star Rating"] != "#NAME?"]
    comps_df = comps_df[
        (comps_df["Star Rating"] >= min_rating)
        & (comps_df["Reviews"] >= min_reviews)
        & (comps_df["Revenue"] >= min_revenue)
        & (comps_df["Occupancy"] >= min_occupancy)
        & (comps_df["Active Nights"] >= min_active_nights)
    ]

    # Fetch titles and create hyperlinks
    asyncio.run(fetch_all_titles(comps_df))

    # Sort DataFrame by 'Revenue'
    comps_df.sort_values(by="Revenue", ascending=False, inplace=True)

    # Create bedroom DataFrames
    bedrooms_dfs = create_bedroom_dfs(comps_df)
    return comps_df, bedrooms_dfs
