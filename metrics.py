#%%
import datetime
from datetime import datetime
from time import sleep
import threading
from multiprocessing import Process
import logging
from dashboard_helpers import readjson


def average_metric(filepath = None ,seconds = 1.0 , key = None):
    if key is None:
        return 'INVALID KEY INPUT for average_metric()'
    metadata = readjson(filepath)
    value = metadata.get(key)
    value = float(value)
    if isinstance(value, float):
        return str( value / seconds )
    else:
        return f"KEY:  {key} for average_metric() is not a number :("
    
    
def clock():
    start_time = datetime.now()
    print(start_time)
    while True:
        if (datetime.now() - start_time).seconds == 1:
            start_time = datetime.now()
            print(start_time)

    # %%

def main():
    average_metric(filepath='logs/staff/taqueros/Omar.json',key = 'stackcounter')

    clock()

