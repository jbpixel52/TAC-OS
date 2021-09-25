# importing the multiprocessing module
import multiprocessing
# Importar el modulo os para sacar IDs de los procesos
import os
# Sleep para simular el proceso de hacer un taco (en verdad no usaremos esto
#  en el proyecto, solo es para hacer una prueba de demostracion 
#  que operaciones en paralelo)
from time import sleep
from time import time
  
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

    # Crear procesos de taqueros, son 4
    #  El orden en que se haran es igual al que se crean
    taqueroROBOT_1 = multiprocessing.Process(target=taco_chico, args=())
    taqueroROBOT_2 = multiprocessing.Process(target=taco_grande, args=())
    taqueroROBOT_3 = multiprocessing.Process(target=taco_XL, args=())
    taqueroROBOT_4 = multiprocessing.Process(target=taco_mediano, args=())
  
    # activar los taqueros dummy de prueba
    #  como dicho en el comentario previo, los taqueros 
    #  simulados seran activdados en cierto orden pero tardarán diferentes
    #  tiempos.  Si en verdad es paralelo el proceso todo tardará 4 segundos
    #   porque ese es el mayor sleep
    start = time()
    taqueroROBOT_1.start()
    taqueroROBOT_2.start()
    taqueroROBOT_3.start()
    taqueroROBOT_4.start()
  
    # Esperar a que los taqueros robots acaben su tareas de "mentis"
    taqueroROBOT_1.join()
    taqueroROBOT_2.join()
    taqueroROBOT_3.join()
    taqueroROBOT_4.join()
    # A pesar que se menciona que debe tardar 4 segundos en total, calculos
    #  en el dispositivo de este autor dice que son 4.9 aproximadamente, no 4
    end = time()

    #Calcular el tiempo total de este simulacro
    print("Simulacro nos tomó: ", end-start)
  
    # both processes finished
    print("Tacos hechos!")