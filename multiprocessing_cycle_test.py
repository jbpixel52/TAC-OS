# importing the multiprocessing module
import multiprocessing
import os
from time import sleep
  
def taco_chico():
    sleep(1)
    print("Taco chico hecho bajo la id {}".format(os.getpid()))

  
def taco_mediano():
    sleep(2)
    print("Taco mediano hecho bajo la id {}".format(os.getpid()))


def taco_grande():
    sleep(3)
    print("Taco grande hecho bajo la id {}".format(os.getpid()))

  
def taco_XL():
    sleep(4)
    print("Taco XL hecho bajo la id {}".format(os.getpid()))

  
if __name__ == "__main__":
    # creating processes
    taqueroROBOT_1 = multiprocessing.Process(target=taco_chico, args=())
    taqueroROBOT_2 = multiprocessing.Process(target=taco_grande, args=())
    taqueroROBOT_3 = multiprocessing.Process(target=taco_XL, args=())
    taqueroROBOT_4 = multiprocessing.Process(target=taco_mediano, args=())
  
    # activar los taqueros dummy de prueba
    taqueroROBOT_1.start()
    taqueroROBOT_2.start()
    taqueroROBOT_3.start()
    taqueroROBOT_4.start()
  
    # Esperar a que los taqueros robots acaben su tareas de "mentis"
    taqueroROBOT_1.join()
    taqueroROBOT_2.join()
    taqueroROBOT_3.join()
    taqueroROBOT_4.join()
  
    # both processes finished
    print("Tacos hechos!")