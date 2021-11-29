import datetime
import json
import logging
import multiprocessing
import threading

import dash
import jsonpickle
import numpy as np
import pandas as pd
import plotly
import plotly.express as px
import plotly.graph_objects as go
from dash import dash_table, dcc, html
from dash.dependencies import Input, Output


def json_to_dataframe(filepath):
    with open(filepath, mode='r') as file:
        data = json.loads(file.read())
        file.close()
    df_nested_orders = pd.json_normalize(data, record_path=['orden'])
    print(df_nested_orders)
    return df_nested_orders


def readjson(filepath):
    data = dict()
    with open(filepath, mode='r') as file:
        data = json.load(file)
        print(data)
        file.close()
    return dict(data)


external_stylesheets = [
    'https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(
    __name__, external_stylesheets=external_stylesheets)

df = json_to_dataframe('jsons.json')


app.layout = html.Div([
    html.H1('TAC-OS DASHBOARD', style={'display': 'inline-block',
            'font-size': 'xxx-large', 'background-color': 'coral'}),
    html.P('ORDERS & SUBORDERS'),
    html.Div([
        dash_table.DataTable(
            id='datatable-interactivity',
            columns=[
                {"name": i, "id": i, "deletable": True, "selectable": True} for i in df.columns
            ],
            data=df.to_dict('records'),
            editable=True,
            filter_action="native",
            sort_action="native",
            sort_mode="multi",
            column_selectable="single",
            row_selectable="multi",
            row_deletable=True,
            selected_columns=[],
            selected_rows=[],
            page_action="native",
            page_current=0,
            page_size=10,
        ),
        html.Div(id='datatable-interactivity-container'),
        #visual aid comment
        
            dcc.Interval(
            id='interval-component',
            interval=1*1000, # in milliseconds
            n_intervals=0
        ),
            
    ])

])


@app.callback(Output('live-update-graph', 'figure'),
              Input('interval-component', 'n_intervals'))
def update_graph_live(n):
    data = json_to_dataframe('logs/staff/taqueros/Omar.json')
    print(data)





#Nota para Julio, eso lo pongo en false para que no se corra dos veces
# la taqueria a la vez, deberá quedarse en false cuando usemos el SQS
def main():
    app.run_server(debug=False, use_reloader=False)
