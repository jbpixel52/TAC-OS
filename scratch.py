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
    
print(taqueroToJSON('logs/staff/taqueros/Omar.json', column = 'ordenes'))


dash_table.DataTable(data = taqueroToJSON('logs/staff/taqueros/Omar.json'))