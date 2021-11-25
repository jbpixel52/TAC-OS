import datetime

import dash
from dash import dcc
from dash import html
import plotly
from dash.dependencies import Input, Output
import plotly.graph_objects as go

class dashboard:
    def __init__(self):
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
                    interval=1*1000,  # in milliseconds
                    n_intervals=0
                )
            ])
        )
        # Multiple components can update everytime interval gets fired.
        @self.app.callback(Output('live-update-graph', 'figure'),
                    Input('interval-component', 'n_intervals'))
        def update_graph_live(self):
            self.fig = go.Figure()
            self.fig.add_trace(go.Scatter(y=[12],x=['taco counter'], mode="lines"), row=1, col=1)
            return self.fig.show()
        
        #RUN DASH APP SERVER    
        self.app.run_server(debug=True)
