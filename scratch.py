#%%
import pandas as pd
import json
from dash import dash_table, html



data = None
with open('outputs/outputs_id_0.json',mode='r') as jsonfile:
    data = json.loads(jsonfile.read())
    jsonfile.close()

df = pd.json_normalize(data).transpose()

table = dash_table.DataTable(data = df.to_dict('records'))

# %%
