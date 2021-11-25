import datetime

import dash
from dash import dcc
from dash import html
import plotly
from dash.dependencies import Input, Output
import main_scheduler as tacos

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

app.layout = html.Div(
    html.Div([
        html.H4('TACO COUNTER'),
        html.Div(id='live-update-text'),
        dcc.Graph(id='live-update-graph'),
        dcc.Interval(
            id='interval-component',
            interval=1*1000, # in milliseconds
            n_intervals=0
        )
    ])
)


@app.callback(Output('live-update-text', 'children'),
              Input('interval-component', 'n_intervals'))
def update_metrics(n):
    pass


# Multiple components can update everytime interval gets fired.
@app.callback(Output('live-update-graph', 'figure'),
              Input('interval-component', 'n_intervals'))
def update_graph_live(n):
    fig = plotly.tools.make_subplots(rows=2, cols=1, vertical_spacing=0.2)
    return fig


if __name__ == '__main__':
    app.run_server(debug=True)