from main_scheduler import CocinaTaqueros, ChalanTaquero, CocinaQuesadillero, PersonalTaqueria, getTime,open_taqueria
import multiprocessing
from multiprocessing import Process, Queue
from queue import Empty
import queue
import threading
import logging
import datetime
import string
import time
import json
import emoji
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


# def main_taqueria():
#     # Solo poner estas ordenes mientras hacemos pruebas
#     ordersToTest = 4
#     logging.basicConfig(level=logging.DEBUG, filename="logfile.log", filemode="a+",
#                         format="%(asctime)-15s %(levelname)-8s %(message)s")
#     print("Scheduler test 1")
#     Cocina = CocinaTaqueros("Taqueros")
#     Cocina.start()
#     Cocina.IngresoPersonal(Cocina)

#     while(True):
#         with open("jsons.json") as OrdenesJSON:
#             ListadoOrdenes = json.load(OrdenesJSON)
#             for i in range(ordersToTest):
#                 orden = ListadoOrdenes[i]
#                 Cocina.personal[0].queue.put(orden)
#         x = input()

def main():
    taqueria = Process(target=open_taqueria)
    taqueria.start()
    
    dashboard = Process(target=dashboard_main.dashboard)
    dashboard.start()


if __name__ == '__main__':
    main()