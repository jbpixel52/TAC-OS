from main_scheduler import open_taqueria
from multiprocessing import Process, Queue
from queue import Empty
import string
import time
from time import sleep
from dash.dependencies import Input, Output
import dashboard_main

abcdario = list(string.ascii_uppercase)
debug_state = True

def main():
    # Este queue contiene jsons con datos acerca de la cocina
    overseerBridge = Queue()
    dashboard = dashboard_main.dashboard("Dashboard", overseerBridge)
    dashboard.start()
    
    #Luego de arrancar el dashboard inica la taqueria
    print("Preparing to boot...")
    open_taqueria(overseerBridge)


if __name__ == '__main__':
    main()
    time.sleep(99999999)