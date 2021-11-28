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


app.layout = html.Div([html.Title('TAC-OS DASHBOARD'),html.H1('TAC-OS DASHBOARD'),html.P('ORDERS'),
                       dash_table.DataTable(
    id='table',
    columns=[{"name": i, "id": i} for i in df.columns],
    data=df.to_dict('records'),
)]
)


def main():
    app.run_server(debug=True)
