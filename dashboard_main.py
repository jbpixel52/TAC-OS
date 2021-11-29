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
        #print(data)
        file.close()
    return dict(data)


df = json_to_dataframe('jsons.json', normal_column='orden')
dfOmar = nested_dict_to_dataframe('logs/staff/taqueros/Omar.json', 'ordenes')

external_stylesheets = [
    'https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(
    __name__, external_stylesheets=external_stylesheets)

app.layout = html.Div([
    html.H1('TAC-OS DASHBOARD', style={'display': 'inline-block',
                                       'font-size': 'xxx-large', 'background-color': 'coral'}),
    html.Div(id='table-div'),
    dcc.Interval(
        id='interval-component',
        interval=2*1000,  # in milliseconds
        n_intervals=0
    )
])

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
        #print(data)
        file.close()
    return dict(data)


df = json_to_dataframe('jsons.json', normal_column='orden')
dfOmar = nested_dict_to_dataframe('logs/staff/taqueros/Omar.json', 'ordenes')

external_stylesheets = [
    'https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(
    __name__, external_stylesheets=external_stylesheets)

app.layout = html.Div([
    html.H1('TAC-OS DASHBOARD', style={'display': 'inline-block',
                                       'font-size': 'xxx-large', 'background-color': 'coral'}),
    html.Div(id='table-div'),
    dcc.Interval(
        id='interval-component',
        interval=2*1000,  # in milliseconds
        n_intervals=0
    )

    # dash_table.DataTable(
    #     id='datatable',
    #     columns=[
    #         {"name": i, "id": i, "deletable": True, "selectable": True} for i in df.columns
    #     ],
    #     data=df.to_dict('records'),
    #     editable=False,
    #     filter_action="native",
    #     sort_action="native",
    #     sort_mode="multi",
    #     column_selectable="single",
    #     row_selectable="multi",
    #     row_deletable=False,
    #     selected_columns=[],
    #     selected_rows=[],
    #     page_action="native",
    #     page_current=0,
    #     page_size=10,
    # ),
    # dash_table.DataTable(
    #     id='datatable_taquero',
    #     data=dfOmar.to_dict('records'),
    #     editable=False,
    #     filter_action="native",
    #     sort_action="native",
    #     sort_mode="multi",
    #     page_action="native",
    #     page_current=0,
    #     page_size=10,
    # ),


])


@app.callback(
    Output('table-div', 'children'),
    Input('interval-component', 'n_intervals')
)
def update(n_intervals):
    if n_intervals > 0:
        # json_to_dataframe(filepath='jsons.json', normal_column='orden').to_dict('records')
        # nested_dict_to_dataframe('logs/staff/taqueros/Omar.json','ordenes').to_dict('records')
        return [
            dash_table.DataTable(
                columns=[
                    {"name": i, "id": i, "deletable": True, "selectable": True} for i in df.columns
                ],
                id='datatable_taquero',
                data=json_to_dataframe(
                    filepath='jsons.json', normal_column='orden').to_dict('records'),
                sort_action="native",
                sort_mode="multi",
                page_action="native",
                page_current=0,
                page_size=10),
                
            dash_table.DataTable(
                columns=[
                    {"name": str(i), "id": str(i)} for i in dfOmar.columns
                ],
                id='datatable_taquero',
                data=dfOmar.to_dict('records'),
                editable=False,
                filter_action="native",
                sort_action="native",
                sort_mode="multi",
                page_action="native",
                page_current=0,
                page_size=10,
            ),
            html.P(f"Is Omar cooking? {get_status('logs/staff/taqueros/Omar.json',key ='cooking')}"),
            html.P(f"Is Omar\'s fan active? {get_status('logs/staff/taqueros/Omar.json',key ='isFanActive')}"),
            html.P(f"Who Is Omar\'s chalan? {get_status('logs/staff/taqueros/Omar.json',key ='chalan')}"),

        ]



def get_status(filepath,key):    
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
        return 'key doesn\'t exist in given metadata dictionary.'
    
    
# Nota para Julio, eso lo pongo en false para que no se corra dos veces
# la taqueria a la vez, deberá quedarse en false cuando usemos el SQS
# LO NECESITO AHORITA
def main():
    app.run_server(debug=True, use_reloader=True)

@app.callback(
    Output('table-div', 'children'),
    Input('interval-component', 'n_intervals')
)
def update(n_intervals):
    if n_intervals > 0:
        # json_to_dataframe(filepath='jsons.json', normal_column='orden').to_dict('records')
        # nested_dict_to_dataframe('logs/staff/taqueros/Omar.json','ordenes').to_dict('records')
        return [
            dash_table.DataTable(
                columns=[
                    {"name": i, "id": i, "deletable": True, "selectable": True} for i in df.columns
                ],
                id='datatable_taquero',
                data=json_to_dataframe(
                    filepath='jsons.json', normal_column='orden').to_dict('records'),
                sort_action="native",
                sort_mode="multi",
                page_action="native",
                page_current=0,
                page_size=10),
                
            dash_table.DataTable(
                columns=[
                    {"name": str(i), "id": str(i)} for i in dfOmar.columns
                ],
                id='datatable_taquero',
                data=dfOmar.to_dict('records'),
                editable=False,
                filter_action="native",
                sort_action="native",
                sort_mode="multi",
                page_action="native",
                page_current=0,
                page_size=10,
            ),
            html.P(f"Is Omar cooking? {get_status('logs/staff/taqueros/Omar.json',key ='cooking')}"),
            html.P(f"Is Omar\'s fan active? {get_status('logs/staff/taqueros/Omar.json',key ='isFanActive')}"),
            html.P(f"Who Is Omar\'s chalan? {get_status('logs/staff/taqueros/Omar.json',key ='chalan')}"),

        ]



def get_status(filepath,key):    
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
        return 'key doesn\'t exist in given metadata dictionary.'
    
    
# Nota para Julio, eso lo pongo en false para que no se corra dos veces
# la taqueria a la vez, deberá quedarse en false cuando usemos el SQS
# LO NECESITO AHORITA
def main():
    app.run_server(debug=True, use_reloader=True)
