import json

import dash
import numpy as np
import pandas as pd
import plotly
import plotly.express as px
import plotly.graph_objects as go
from dash import dash_table, dcc, html
from dash.dependencies import Input, Output

from dashboard_helpers import (get_status, json_to_dataframe,
                               nested_dict_to_dataframe, read_log, readjson,
                               staff_metadata_html)
metada_style = {'display': 'flex', 'flex-direction': 'row', 'justify-content': 'space-evenly', 'max-width': '90%', 'align-items': 'center'}
LOGLINE = 0
OMARPATH = 'logs/staff/taqueros/Omar.json'


df = json_to_dataframe('jsons.json', normal_column='orden')
dfOmar = nested_dict_to_dataframe('logs/staff/taqueros/Omar.json', 'ordenes')

external_stylesheets = [
    'https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(
    __name__, external_stylesheets=external_stylesheets)

app.layout = html.Div([
    html.Div(id='table-div', style={'background-color': 'FloralWhite'}),
    dcc.Interval(
        id='interval-component',
        interval=2*1000,  # in milliseconds
        n_intervals=0
    )
])


@app.callback(
    Output('table-div', 'children'),
    Input('interval-component', 'n_intervals')
)
def update(n_intervals):
    if n_intervals > 0:
        return [
            html.H1('TAC-OS DASHBOARD', style={'display': 'inline-block',
                                               'font-size': 'xxx-large', 'background-color': 'SlateBlue'}),

            html.Div(style={'display': 'flex', 'flex-direction': 'row', 'justify-content': 'space-evenly', 'max-width': '90%', 'align-items': 'center'},
                     children=[
                dash_table.DataTable(
                    columns=[
                        {"name": i, "id": i, "deletable": True, "selectable": True} for i in df.columns
                    ],
                    id='datatable_taquero',
                    data=json_to_dataframe(
                        filepath='jsons.json', normal_column='orden').to_dict('records'),
                    sort_action="native",
                    page_action="native",
                    page_current=0,
                    style_cell={'padding': '5px',
                                'background-color': 'FloralWhite'},
                    page_size=10),

                dash_table.DataTable(
                    columns=[
                        {"name": str(i), "id": str(i)} for i in dfOmar.columns
                    ],
                    id='datatable_taquero',
                    data=nested_dict_to_dataframe(
                        'logs/staff/taqueros/Omar.json', 'ordenes').to_dict('records'),
                    editable=False,
                    style_cell={'padding': '5px',
                                'background-color': 'FloralWhite'},
                    sort_action="native",
                    page_action="native",
                    page_current=0,
                    page_size=10,
                ), ]),
            # METADA DE LOS TAQUERO
            html.Div(children=staff_metadata_html(),style=metada_style),
            #######
            html.H2('TAC-OS LOGS'),
            html.Div(children=read_log('logfile.log'), style={
                     'overflow': 'auto', 'height': '200px', 'background-color': 'SlateBlue'}),

        ]


def tableandtile(title, table):
    pass


def main():
    app.run_server(debug=False, use_reloader=False)
