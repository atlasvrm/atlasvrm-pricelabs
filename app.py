import dash
import os
import logging
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table
from dash.dependencies import Input, Output, State
from utilities.pricelabs_utils import (
    process_comps,
    process_uploaded_files,
    create_br_dt,
    create_columns,
)
from dash.exceptions import PreventUpdate

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Initialize the Dash app with a Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CERULEAN])

# Filter parameters
MIN_RATING = 4.5
MIN_REVIEWS = 10
MIN_REVENUE = 10000
MIN_OCCUPANCY = 0.30
MIN_ACTIVE_NIGHTS = 180

# Create a list of tabs for different bedroom counts using a for loop
bedroom_tabs = []
for i in range(2, 7):
    tab = dbc.Tab(
        label=f"{i}BR Comps",
        tab_id=f"{i}br-comps",
        children=[create_br_dt(f"{i}br-comps")],
    )
    bedroom_tabs.append(tab)

# App layout using Dash Bootstrap Components
app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    dcc.Input(
                        id="input-market-name",
                        type="text",
                        placeholder="Enter Market Name",
                        value="",
                        style={"width": "100%"},
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
                        accept=".csv",
                    ),
                    width=6,
                )
            ]
        ),
        dbc.Row([dbc.Col(html.Div(id="output-data-upload"), width=12)]),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Tabs(
                        [
                            dbc.Tab(
                                label="Raw Comps",
                                tab_id="raw-comps",
                                children=[
                                    dash_table.DataTable(
                                        id="comps-table",
                                        style_cell={"textAlign": "center"},
                                    )
                                ],
                            ),
                            dbc.Tab(
                                label="Raw Trends",
                                tab_id="raw-trends",
                            ),
                            dbc.Tab(
                                label="Market Summary",
                                tab_id="market-summary",
                            ),
                        ]
                        + bedroom_tabs,
                        id="tabs",
                        active_tab="raw-comps",
                    ),
                    width=12,
                )
            ]
        ),
    ],
    fluid=True,
)


@app.callback(
    Output("comps-table", "data"),
    Output("comps-table", "columns"),
    Input("upload-comps", "contents"),
    State("upload-comps", "filename"),
    State("input-market-name", "value"),
)
def update_and_initialize(comps_contents, comps_filename, input_market_name):
    print("comps_contents", comps_contents)
    if not comps_contents:
        return [], []

    market_dir = os.path.join("Markets", input_market_name)
    processed_filepath = os.path.join(market_dir, "processed_comps.csv")
    print("Processed Filepath:", processed_filepath)
    comps_df = process_uploaded_files(comps_contents, comps_filename, market_dir)
    print("comps_df", comps_df)
    comps_processed = process_comps(
        comps_df, MIN_RATING, MIN_REVIEWS, MIN_REVENUE, MIN_OCCUPANCY, MIN_ACTIVE_NIGHTS
    )
    print("comps_processed", comps_processed)

    comps_processed.to_csv(processed_filepath, index=False)

    comps_columns = create_columns(comps_processed)
    comps_data = comps_processed.to_dict("records")
    print("comps_data", comps_data)

    return comps_data, comps_columns


# Run the app
if __name__ == "__main__":
    app.run_server(debug=True)
