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

LOGLINE = 0
OMARPATH = 'logs/staff/taqueros/Omar.json'


def read_log(filepath=None):
    HTMLparagraphs = []
    with open(filepath, mode='r') as file:
        for line in file:
            HTMLparagraphs.append(html.P(line))
        file.close()
    return HTMLparagraphs


def json_to_dataframe(filepath, normal_column=None):
    if normal_column is None:
        return pd.read_json(filepath)
    elif normal_column is not None:
        with open(filepath, mode='r') as file:
            data = json.loads(file.read())
            df_nested = pd.json_normalize(
                data, record_path=[str(normal_column)])
            file.close()
        return df_nested


def nested_dict_to_dataframe(filepath, column):
    with open(filepath, mode='r') as file:
        data = json.load(file)
        file.close()
    df = pd.DataFrame(data.get(column)).transpose()
    return df


def readjson(filepath):
    data = dict()
    with open(filepath, mode='r') as file:
        data = json.load(file)
        # print(data)
        file.close()
    return dict(data)


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
                    style_cell={'padding': '5px','background-color':'FloralWhite'},
                    page_size=10),

                dash_table.DataTable(
                    columns=[
                        {"name": str(i), "id": str(i)} for i in dfOmar.columns
                    ],
                    id='datatable_taquero',
                    data=nested_dict_to_dataframe(
                        'logs/staff/taqueros/Omar.json', 'ordenes').to_dict('records'),
                    editable=False,
                    style_cell={'padding': '5px','background-color':'FloralWhite'},
                    sort_action="native",
                    page_action="native",
                    page_current=0,
                    page_size=10,
                ), ]),
            # METADA DEL TAQUERO
            html.H2(f"Metadata del taquero {get_status(OMARPATH, 'name')}", style={
                    'background-color': 'CornflowerBlue', 'max-width': '20%'}),
            html.P(
                f"Is Omar cooking? {get_status(OMARPATH,key ='cooking')}"),
            html.P(
                f"Is Omar\'s fan active? {get_status(OMARPATH,key ='isFanActive')}"),
            html.P(
                f"Who Is Omar\'s chalan? {get_status(OMARPATH,key ='chalan')}"),
            html.P(
                f"Omar\'s remaining Cilantro: {get_status(OMARPATH,key ='currentCilantro')}"),
            html.P(
                f"Omar\'s remaining Cebolla: {get_status(OMARPATH,key ='currentCebolla')}"),
            html.P(
                f"Omar\'s remaining Tortillas: {get_status(OMARPATH,key ='currentTortillas')}"),
            html.P(
                f"Omar\'s remaining Salsa: {get_status(OMARPATH,key ='currentSalsa')}"),
            html.P(
                f"Omar\'s remaining Guacamole: {get_status(OMARPATH,key ='currentGuacamole')}"),
            html.P(
                f"Omar is working the order: {get_status(OMARPATH,key ='currentWorkingOrder')}"),
            html.P(
                f"Omar is working the suborder: {get_status(OMARPATH,key ='currentWorkingSuborder')}"),

            #######
            html.H2('TAC-OS LOGS'),
            html.Div(children=read_log('logfile.log'), style={
                     'overflow': 'auto', 'height': '200px', 'background-color': 'SlateBlue'}),

        ]

def tableandtile(title,table):
    pass


def get_status(filepath, key):
    metadata = readjson(filepath)
    if key in metadata:
        if metadata.get(key) is True:
            if key == 'cooking' or 'isFanActive':
                return 'YES'
            else:
                return metada.get(key)
        elif metadata.get(key) is False:
            if key == 'cooking' or 'isFanActive':
                return 'NO'
            else:
                return metada.get(key)
        else:
            # ESTO ES PARA LOS CASOS COMO NOMBRES O NON BINARY VALUES
            return metadata.get(key)
    else:
        return 'key doesn\'t exist in given metadata dictionary.'


def main():
    app.run_server(debug=False, use_reloader=False)
