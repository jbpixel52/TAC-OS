import jsonpickle
import logging
import multiprocessing
import json
import threading
import datetime
import numpy as np
import dash
from dash import dcc
from dash import html
import plotly
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go

class dashboard():
    def __init__(self):
        #super(dashboard, self).__init__(target=self.main, name=_name)
        #self.commsChannel = Bridge
        # self.recieverThread = threading.Thread(
        #     target = self.recieverFunction,
        #     args = ()
        # )
        self.main()

    def recieverFunction(self):
        while(True):
            #print(self.commsChannel.get())
            pass
    

    
    def main(self): 
        self.external_stylesheets = [
            'https://codepen.io/chriddyp/pen/bWLwgP.css']

        self.app = dash.Dash(
            __name__, external_stylesheets=self.external_stylesheets)

        self.app.layout = html.Div(
            html.Div([
                html.H4('TACO COUNTER'),
                html.Div(id='live-update-text'),
                dcc.Graph(id='live-update-graph'),
                dcc.Interval(
                    id='interval-component',
                    interval=5*1000,  # in milliseconds
                    n_intervals=0
                )
            ])
        )
        
        # Multiple components can update everytime interval gets fired.
        @self.app.callback(Output('live-update-graph', 'figure'),
                    Input('interval-component', 'n_intervals'))
        def update_graph_live(self):
            pass
            # data = readjson('logs/staff/taqueros/Omar.json')
            
            # ydata = [0,int(data['stackcounter'])]
            # t = np.linspace(len())
            # self.fig = px.line(x=t, y=, labels={'x':'time', 'y':'stack counter'})
            # return self.fig.show()
        
        #RUN DASH APP SERVER    
        self.app.run_server(debug=True) 


def readjson(filepath):
    with open(filepath,mode='r') as file:
        data = json.load(file)
        print(data)
        return data