import pandas as pd
import json


import dash
import dash_table
import pandas as pd


def json_to_dataframe(filepath):
    with open(filepath, mode='r') as file:
        data = json.loads(file.read())
        file.close()
    df_nested_orders = pd.json_normalize(data, record_path=['orden'])
    print(df_nested_orders)
    return df_nested_orders
df = json_to_dataframe('jsons.json')
app = dash.Dash(__name__)

app.layout = dash_table.DataTable(
    id='table',
    columns=[{"name": i, "id": i} for i in df.columns],
    data=df.to_dict('records'),
)

if __name__ == '__main__':
    app.run_server(debug=True)