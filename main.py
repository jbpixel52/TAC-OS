import datetime
import json
import logging
import multiprocessing
import queue
import string
import sys
import threading
import time
from multiprocessing import Process, Queue
from queue import Empty
from time import sleep

import dash
import numpy as np
import pandas as pd
import plotly
import plotly.express as px
import plotly.graph_objects as go
from dash import dash_table, dcc, html
from dash.dependencies import Input, Output

import dashboard_main
from main_scheduler import (ChalanTaquero, CocinaTaqueros,
                            PersonalTaqueria, getTime, open_taqueria)
import metrics
debug_state = False

def main():
    taqueria = Process(target = open_taqueria)
    taqueria.start()
    dashboard = Process(target = dashboard_main.main())
    performance = Process(target= metrics.main())
    performance.start()
    dashboard.start()



if __name__ == '__main__':
    main()
    while(True):
        time.sleep(99)
