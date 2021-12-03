#%%
import pandas as pd
import json
from dash import dash_table, html



def taqueroToJSON(filepath = None,column=None):
    with open(filepath, mode='r') as file:
        data = json.load(file)
        file.close()
    df = pd.DataFrame(data.get(column)).transpose()
    return df
    
DataFrame = taqueroToJSON('logs/staff/taqueros/Omar.json',column='ordenes')
dash_table.DataTable(data = DataFrame)

df = json_to_dataframe('jsons.json',normal_column='orden')

"""elements_list.append(dash_table.DataTable(
    columns=[
        {"name": i, "id": i, "deletable": True, "selectable": True} for i in df.columns
    ],
    id='global-orders',
    data=json_to_dataframe(
        filepath='jsons.json', normal_column='orden').to_dict('records'),
    sort_action="native",
    page_action="native",
    page_current=0,
    page_size=5))"""

