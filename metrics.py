#%%
import datetime
from datetime import datetime
from time import sleep
import threading
from multiprocessing import Process

def clock():
    start_time = datetime.now()
    print(start_time)
    while True:
        if (datetime.now() - start_time).seconds == 1:
            start_time = datetime.now()
            print(start_time)

    # %%


