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
import jsonpickle
import numpy as np
import pandas as pd
import plotly
import plotly.express as px
import plotly.graph_objects as go
from dash import dash_table, dcc, html
from dash.dependencies import Input, Output

import dashboard_main
from main_scheduler import (ChalanTaquero, CocinaQuesadillero, CocinaTaqueros,
                            PersonalTaqueria, getTime, open_taqueria)

abcdario = list(string.ascii_uppercase)

debug_state = False

programas = multiprocessing.Queue()


def main():
    taqueria = Process(target=open_taqueria)
    taqueria.start()
    dashboard = Process(target=dashboard_main.main())
    dashboard.start()


if __name__ == '__main__':
    main()
    while(True):
        time.sleep(99)
