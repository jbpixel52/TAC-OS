#%%
import datetime
from time import sleep
def nowTime():
    return datetime.datetime.now()
    


EPOCH = getTime()
ENDTIMES = None
DELTATIME = None

while True:
    sleep(1)
    ENDTIMES = getTime()
    DELTATIME = ENDTIMES - EPOCH
    print(DELTATIME)