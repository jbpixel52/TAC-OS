#%%
import pandas as pd
import json
from dash import dash_table, html
from time import sleep
from datetime import datetime,timedelta

EPOCHTIME= datetime.now()
NOW = datetime.now()
DIF = NOW-EPOCHTIME

print(f"{(datetime.now()-EPOCHTIME).total_seconds() * 1000:.2f}ms")
# %%
