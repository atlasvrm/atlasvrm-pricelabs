import dash
import os
import logging
import pandas as pd
import dash_bootstrap_components as dbc
from dash import html, dcc, dash_table, ctx
from dash.dependencies import Input, Output, State
from utilities.pricelabs_utils import process_comps, process_uploaded_files
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
                    dash_table.DataTable(
                        id="output-table",
                        style_cell={"textAlign": "center"},
                    ),
                    width=12,
                )
            ]
        ),
    ],
    fluid=True,
)


# Combined callback for initialization and file processing
@app.callback(
    [
        Output("input-market-name", "value"),
        Output("output-data-upload", "children"),
        Output("output-table", "data"),
        Output("output-table", "columns"),
        Output("session-store", "data"),
    ],
    [
        Input("upload-comps", "contents"),
        Input("session-store", "data"),
    ],
    [
        State("upload-comps", "filename"),
        State("input-market-name", "value"),
    ],
)
def update_and_initialize(
    comps_contents,
    session_store_data,
    comps_filename,
    input_market_name,
):
    try:
        trigger_id = ctx.triggered[0]["prop_id"] if ctx.triggered else None

        # Check what triggered the callback
        if trigger_id and "session-store" in trigger_id:
            # Initialize from stored data
            if session_store_data:
                market_name = session_store_data.get("market_name", "")
                processed_filepath = session_store_data.get("processed_filepath")
                if processed_filepath and os.path.exists(processed_filepath):
                    comps_processed = pd.read_csv(processed_filepath)
                    columns = [
                        {
                            "name": i,
                            "id": i,
                            "type": "text",
                            "presentation": "markdown"
                            if i == "Listing Title"
                            else None,
                        }
                        for i in comps_processed.columns
                    ]
                    data = comps_processed.to_dict("records")
                    return (
                        market_name,
                        dbc.Alert(
                            f"Data loaded from '{market_name}'.", color="success"
                        ),
                        data,
                        columns,
                        dash.no_update,
                    )
            raise PreventUpdate

        # Logic for processing new uploads
        if comps_contents and input_market_name:
            market_dir = os.path.join("Markets", input_market_name)
            comps_df = process_uploaded_files(
                comps_contents, comps_filename, market_dir
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
                "market_name": input_market_name,
                "market_dir": market_dir,
                "processed_filepath": output_filepath,
                "data_table": data,
            }

            return (
                input_market_name,
                dbc.Alert(
                    f"Comps and trends data have been uploaded and processed. Results saved in '{market_dir}'.",
                    color="success",
                ),
                data,
                columns,
                store_data,
            )

        return "", None, [], [], None

    except PreventUpdate:
        logging.info("update_and_initialize callback did not update (PreventUpdate).")
        raise

    except Exception as e:
        logging.error(f"Error in update_and_initialize callback: {e}", exc_info=True)
        return "", dbc.Alert(f"An error occurred: {e}", color="danger"), [], [], None


# Run the app
if __name__ == "__main__":
    app.run_server(debug=True)
