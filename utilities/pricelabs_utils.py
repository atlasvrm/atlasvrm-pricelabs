import geopandas as gpd
from shapely.geometry import Point
import pandas as pd
import requests
from bs4 import BeautifulSoup


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


def get_airbnb_title(page_url):
    """Extracts HTML from a webpage and gets the title."""
    try:
        answer = requests.get(page_url)
        content = answer.content
        soup = BeautifulSoup(content, features="html.parser")
        title1 = soup.find("meta", property="og:description")
        if title1 is not None and "content" in title1.attrs:
            listing_name = title1["content"]
        else:
            listing_name = "N/A"  # Set a default value if the title is not found
    except Exception as e:
        listing_name = "N/A"  # Set a default value if any exception occurs
    return listing_name
