import geopandas as gpd

import os
from dash import dash_table
from dash.dash_table import FormatTemplate
from shapely.geometry import Point
import pandas as pd
from bs4 import BeautifulSoup
import io
import base64
import dash_bootstrap_components as dbc
import aiohttp
import asyncio
from threading import Thread


def get_market_names():
    market_dir = "Markets/"
    if not os.path.exists(market_dir):
        os.makedirs(market_dir)
    return [
        name
        for name in os.listdir(market_dir)
        if os.path.isdir(os.path.join(market_dir, name))
    ]


def create_br_dt(tab_id):
    return dash_table.DataTable(
        id=f"{tab_id}-table",
        style_cell={"textAlign": "center"},
        style_data_conditional=[
            {
                "if": {"column_id": "Listing Title"},
                "className": "markdown-cell",
            }
        ],
        columns=[
            {
                "name": "Listing Title",
                "id": "Listing Title",
                "type": "text",
                "presentation": "markdown",
            },
            {
                "name": "Revenue",
                "id": "Revenue",
                "type": "numeric",
                "format": FormatTemplate.money(0),
            },
            {
                "name": "Occupancy",
                "id": "Occupancy",
                "type": "numeric",
                "format": FormatTemplate.percentage(2),
            },
        ],
    )


def create_columns(df):
    return [
        {
            "name": i,
            "id": i,
            "type": "text",
            "presentation": "markdown" if i == "Listing Title" else None,
        }
        for i in df.columns
    ]


def run_async_tasks(comps_df):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(fetch_all_titles(comps_df))
    loop.close()


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


def process_uploaded_files(comps_contents, comps_filename, market_dir):
    if not os.path.exists(market_dir):
        os.makedirs(market_dir)

    # Save raw files
    raw_comps_path = os.path.join(market_dir, "raw_comps.csv")
    save_raw_file(comps_contents, raw_comps_path)

    # Process files
    comps_df = parse_contents(comps_contents, comps_filename)

    return comps_df


def save_raw_file(contents, filepath):
    decoded_contents = base64.b64decode(contents.split(",")[1])
    with open(filepath, "wb") as f:
        f.write(decoded_contents)


def process_comps(
    comps_df, min_rating, min_reviews, min_revenue, min_occupancy, min_active_nights
):
    # Convert 'Star Rating' to numeric and drop NA values

    comps_df["Star Rating"] = pd.to_numeric(comps_df["Star Rating"], errors="coerce")
    comps_df.dropna(subset=["Star Rating"], inplace=True)

    # Remove rows where "Star Rating" equals "#NAME?"
    comps_df = comps_df[comps_df["Star Rating"] != "#NAME?"]

    # Convert Occupancy to decimal
    comps_df["Occupancy"] = comps_df["Occupancy"] / 100
    # Apply filters using .loc for safe modification
    condition = (
        (comps_df["Star Rating"] >= min_rating)
        & (comps_df["Reviews"] >= min_reviews)
        & (comps_df["Revenue"] >= min_revenue)
        & (comps_df["Occupancy"] >= min_occupancy)
        & (comps_df["Active Nights"] >= min_active_nights)
    )
    filtered_df = comps_df.loc[condition].copy()

    # Define a function to run the async task
    def run_async(loop, df):
        asyncio.set_event_loop(loop)
        loop.run_until_complete(fetch_all_titles(df))

    # Create a new event loop for the thread
    loop = asyncio.new_event_loop()

    # Run async tasks in a background thread
    thread = Thread(target=run_async, args=(loop, filtered_df))
    thread.start()
    thread.join()  # This will block until the async task is done

    # Continue processing after async tasks are complete
    filtered_df.sort_values(by="Revenue", ascending=False, inplace=True)

    return filtered_df


def create_br_dt(tab_id):
    return dash_table.DataTable(
        id=f"{tab_id}-table",
        style_cell={"textAlign": "center"},
        columns=[
            {
                "name": "Listing Title",
                "id": "Listing Title",
                "type": "text",
                "presentation": "markdown",
            },
            {
                "name": "Revenue",
                "id": "Revenue",
                "type": "numeric",
                "format": FormatTemplate.money(0),
            },
            {
                "name": "Occupancy",
                "id": "Occupancy",
                "type": "numeric",
                "format": FormatTemplate.percentage(0),
            },
        ],
    )
