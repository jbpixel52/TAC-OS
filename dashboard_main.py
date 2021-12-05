import json

import dash
import numpy as np
import pandas as pd
import plotly
import plotly.express as px
import plotly.graph_objects as go
from dash import dash_table, dcc, html
from dash.dependencies import Input, Output

import dashboard_helpers as helpers


app = dash.Dash(
    __name__, external_stylesheets=['style.css'])

app.layout = html.Div([
    html.Div(id='table-div',children=[]),
    dcc.Interval(
        id='interval-component',
        interval=1*1000,  # in milliseconds
        n_intervals=2
    )
])


@app.callback(
    Output('table-div', 'children'),
    Input('interval-component', 'n_intervals')
)
def update(n_intervals):
    if n_intervals > 0:
        return [
            html.H1('TAC-OS 🌮'),
            html.Div(id='metadata-div', children=helpers.staff_metadata_html()),
            html.H2('TAC-OS LOGS'),
            html.Div(id='log-div', children=helpers.read_log('logfile.log')),
            html.Div(id='tables-div',children=helpers.Tables()),
            html.Div(id='outputs',children=helpers.outputsTables(directory='outputs/'))
        ]

def main():
    app.run_server(debug=True, use_reloader=False, dev_tools_hot_reload=True)
