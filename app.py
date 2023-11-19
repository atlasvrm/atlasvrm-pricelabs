import dash
import os
import logging
import pandas as pd
from dash import callback_context
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table
from dash.dependencies import Input, Output, State
from utilities.pricelabs_utils import (
    process_comps,
    process_uploaded_files,
    create_br_dt,
    create_columns,
    get_market_names,
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

market_names = get_market_names()
market_dropdown_options = [{"label": name, "value": name} for name in market_names]
market_dropdown_options.append({"label": "Add New Market...", "value": "new_market"})

# Lists for tab properties
labels = ["Raw Comps", "Raw Trends", "Market Summary"] + [
    f"{i}BR Comps" for i in range(2, 7)
]
tab_ids = ["raw-comps", "raw-trends", "market-summary"] + [
    f"{i}br-comps" for i in range(2, 7)
]
contents = [
    dash_table.DataTable(
        id="comps-table",
        filter_action="native",
        sort_action="native",
        sort_mode="multi",
        column_selectable="multi",
        row_selectable="multi",
        style_cell={"textAlign": "center"},
    ),
    None,  # Replace with actual content for "Raw Trends"
    None,  # Replace with actual content for "Market Summary"
] + [create_br_dt(f"{i}br-comps") for i in range(2, 7)]

# Generate dbc.Tab components
tabs = [
    dbc.Tab(label=label, tab_id=tab_id, children=content)
    for label, tab_id, content in zip(labels, tab_ids, contents)
]


# App layout using Dash Bootstrap Components
app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        dcc.Dropdown(
                            id="input-market-name",
                            options=market_dropdown_options,
                            value=market_names[0] if market_names else "new_market",
                            style={"width": "100%"},
                        ),
                        html.Div(
                            [
                                dcc.Input(
                                    id="new-market-name",
                                    type="text",
                                    placeholder="Enter new market name",
                                ),
                                html.Button(
                                    "Submit", id="submit-new-market", n_clicks=0
                                ),
                            ],
                            id="new-market-name-input",
                            style={"display": "none"},
                        ),
                    ],
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
                        tabs,
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
    [
        Output("input-market-name", "options"),
        Output("input-market-name", "value"),
        Output("new-market-name-input", "style"),
    ],
    [
        Input("submit-new-market", "n_clicks"),
        Input("input-market-name", "value"),
    ],
    [
        State("new-market-name", "value"),
        State("input-market-name", "options"),
    ],
)
def handle_market_changes(n_clicks, dropdown_value, new_market_name, current_options):
    # Initialize default return values
    input_style = {"display": "none"}  # Default style to hide new market input
    updated_options = current_options  # Default to current options
    updated_value = dash.no_update  # Keep current value by default

    triggered_id = callback_context.triggered[0]["prop_id"].split(".")[0]

    # Handle new market submission
    if triggered_id == "submit-new-market" and n_clicks > 0:
        if new_market_name and new_market_name not in [
            opt["value"] for opt in current_options
        ]:
            # Create new market folder
            new_market_dir = os.path.join("Markets", new_market_name)
            os.makedirs(new_market_dir, exist_ok=True)

            # Update dropdown options
            updated_options = [
                {"label": name, "value": name} for name in get_market_names()
            ]
            updated_options.append(
                {"label": "Add New Market...", "value": "new_market"}
            )

            # Update dropdown value to the newly created market
            updated_value = new_market_name

    # Handle dropdown value change
    elif triggered_id == "input-market-name":
        if dropdown_value == "new_market":
            input_style = {"display": "block"}

    return updated_options, updated_value, input_style


@app.callback(
    Output("comps-table", "data"),
    Output("comps-table", "columns"),
    Input("upload-comps", "contents"),
    State("upload-comps", "filename"),
    State("input-market-name", "value"),
)
def update_and_initialize(comps_contents, comps_filename, input_market_name):
    if not comps_contents:
        return [], []

    market_dir = os.path.join("Markets", input_market_name)
    processed_filepath = os.path.join(market_dir, "processed_comps.csv")
    comps_df = process_uploaded_files(comps_contents, comps_filename, market_dir)
    comps_processed = process_comps(
        comps_df, MIN_RATING, MIN_REVIEWS, MIN_REVENUE, MIN_OCCUPANCY, MIN_ACTIVE_NIGHTS
    )

    comps_processed.to_csv(processed_filepath, index=False)

    comps_columns = create_columns(comps_processed)
    comps_data = comps_processed.to_dict("records")

    return comps_data, comps_columns


# Callback to update the bedroom comps tables
@app.callback(
    [Output(f"{i}br-comps-table", "data") for i in range(2, 7)],
    [
        Input("comps-table", "data"),
        Input("tabs", "active_tab"),
    ],
)
def update_bedroom_comps_tables(comps_data, active_tab):
    try:
        # Check if the active tab is one of the bedroom comps tabs
        if comps_data and active_tab.endswith("br-comps"):
            bedroom_count = int(active_tab[0])
            bedroom_df = pd.DataFrame(comps_data)
            filtered_data = (
                bedroom_df[bedroom_df["Bedrooms"] <= bedroom_count]
                .sort_values(by="Revenue", ascending=False)
                .to_dict("records")
            )

            # Return the filtered data for each tab
            return tuple(
                filtered_data if str(i) in active_tab else [] for i in range(2, 7)
            )

    except Exception as e:
        logging.error(f"Error: {e}", exc_info=True)
        # Return empty data for each table in case of an error
        return tuple([] for _ in range(2, 7))

    # Return empty data for each table if the conditions are not met
    return tuple([] for _ in range(2, 7))


# Run the app
if __name__ == "__main__":
    app.run_server(debug=True)
