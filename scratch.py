
#%%
LOGLINE=0

def read_log(filepath=None):
    with open(filepath,mode='r') as file:
        for line in file:
            print(line)
            

read_log('logfile.log')