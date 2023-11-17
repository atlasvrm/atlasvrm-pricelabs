import dash
import os
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table
from dash.dependencies import Input, Output, State
from utilities.pricelabs_utils import (
    process_comps,
    process_uploaded_files,
)

# Initialize the Dash app with a Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Filter parameters
MIN_RATING = 4.5
MIN_REVIEWS = 10
MIN_REVENUE = 10000
MIN_OCCUPANCY = 30
MIN_ACTIVE_NIGHTS = 180

# App layout using Dash Bootstrap Components
app.layout = dbc.Container(
    [
        dcc.Store(id="session-store", storage_type="local"),
        dbc.Row(
            [
                dbc.Col(
                    dcc.Input(
                        id="input-market-name",
                        type="text",
                        placeholder="Enter Market Name",
                        style={"width": "100%"},  # Adjust width as needed
                    ),
                    width=6,
                ),
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    dcc.Upload(
                        id="upload-comps",
                        children=dbc.Button("Upload Comps Data", color="primary"),
                        multiple=False,
                        accept=".csv",  # Accept only CSV files
                    ),
                    width=6,
                )
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    dcc.Upload(
                        id="upload-trends",
                        children=dbc.Button("Upload Trends Data", color="primary"),
                        multiple=False,
                        accept=".csv",  # Accept only CSV files
                    ),
                    width=6,
                )
            ]
        ),
        dbc.Row([dbc.Col(html.Div(id="output-data-upload"), width=12)]),
        dbc.Row([dbc.Col(dash_table.DataTable(id="output-table"), width=12)]),
    ],
    fluid=True,
)


# Callback for file uploads and processing
@app.callback(
    [
        Output("output-data-upload", "children"),
        Output("output-table", "data"),
        Output("output-table", "columns"),
        Output("session-store", "data"),  # Output to update the store
    ],
    [
        Input("upload-comps", "contents"),
        Input("upload-trends", "contents"),
        Input("input-market-name", "value"),
    ],
    [State("upload-comps", "filename"), State("upload-trends", "filename")],
)
def update_output(
    comps_contents, trends_contents, market_name, comps_filename, trends_filename
):
    if comps_contents and trends_contents and market_name:
        market_dir = os.path.join("Markets", market_name)
        comps_df, trends_df = process_uploaded_files(
            comps_contents, trends_contents, comps_filename, trends_filename, market_dir
        )

        comps_processed, bedrooms_dfs = process_comps(
            comps_df,
            MIN_RATING,
            MIN_REVIEWS,
            MIN_REVENUE,
            MIN_OCCUPANCY,
            MIN_ACTIVE_NIGHTS,
        )

        output_filepath = os.path.join(market_dir, "processed_comps.csv")
        comps_processed.to_csv(output_filepath, index=False)

        columns = [
            {
                "name": i,
                "id": i,
                "type": "text",
                "presentation": "markdown" if i == "Listing Title" else None,
            }
            for i in comps_processed.columns
        ]
        data = comps_processed.to_dict("records")

        store_data = {
            "market_dir": market_dir,
            "processed_filepath": output_filepath,
            # Any other data you want to store
        }

        return (
            dbc.Alert(
                f"Comps and trends data have been uploaded and processed. "
                f"Results saved in '{market_dir}'.",
                color="success",
            ),
            data,
            columns,
            store_data,  # Return the store data
        )

    return (
        dbc.Alert(
            "Please upload both Comps and Trends data and enter a market name.",
            color="warning",
        ),
        [],
        [],
        None,  # Return None for the store when there's no update
    )


# Run the app
if __name__ == "__main__":
    app.run_server(debug=True)
