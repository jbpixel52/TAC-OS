from main_scheduler import CocinaTaqueros, ChalanTaquero, CocinaQuesadillero, PersonalTaqueria, getTime,open_taqueria
import multiprocessing
from multiprocessing import Process, Queue
from queue import Empty
import queue
import threading
import logging
import json
import datetime
import string
import time
import numpy as np
import json
from time import sleep
import sys
import datetime
import dash
from dash import dcc
from dash import html
import plotly
from dash.dependencies import Input, Output
import dashboard_main

abcdario = list(string.ascii_uppercase)

debug_state = True

programas = multiprocessing.Queue()


def main():
    taqueria = Process(target=open_taqueria)
    taqueria.start()
   # dashboard = Process(target=dashboard_main.dashboard)
   # dashboard.start()
   


if __name__ == '__main__':
    main()
    while(True):
        time.sleep(99)