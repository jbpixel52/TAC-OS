#%%
import multiprocessing
import threading
import logging
import datetime
import time
import sched

s = sched.scheduler(time.time, time.sleep)

def getTime():
    LocalTime = datetime.datetime.now().strftime("%H:%M:%S")
    return LocalTime

class PersonalTaqueria(threading.Thread):
    def __init__(self,nombre):
        #SuperConstructor
        super(PersonalTaqueria, self).__init__(target = self.main, name = nombre)
        self.queue = multiprocessing.Queue()
        self.OrderRecieverThread = threading.Thread(
            target = self.recieveClientOrders,
            args = ()
        )
        self.CookerThread = threading.Thread(
            target = self.cook,
            args = ()
        )
        self.ordersPerSecondDelta = 3 #^-1 
        self.cookUnitDelta = 0.5 #Minimo para cocinar
        self.Rescheduling = False
        self.ordenes = {} #dict in mind per worker
        self.tacoCounter=0
    def main(self):
        # Formato de prueba
        #  Orden  = (tiempollegada,duracionOrden)
        print(f"Taquero {self.name} en linea")

        self.OrderRecieverThread.start()
        self.CookerThread.start()


    def recieveClientOrders(self):
        while(True):
            print(f"{self.ordenes}")

            try:
                newOrder = self.queue.get_nowait()
                self.tacoCounter=+1
                self.ordenes[str(self.tacoCounter)]=newOrder
                self.Rescheduling = True
                #self.ordenes.sort()
                self.Rescheduling = False
            except:
                pass
            time.sleep(self.ordersPerSecondDelta)
    
    def cook(self):
        while(True):
            try:
                shortestOrder = min(self.ordenes) #orden mas corta en el self.orden
                if self.ordenes[shortestOrder]>0 and (not self.Rescheduling):
                    self.ordenes[shortestOrder]-=self.cookUnitDelta #resta el costo del taco hecho
                else:
                    self.ordenes.pop(shortestOrder,None) #saca orden del taquero
                time.sleep(self.cookUnitDelta)            
            except:
              pass


class CocinaTaqueros(multiprocessing.Process):
    def __init__(self,_name):
        #SuperConsteructor
        super(CocinaTaqueros, self).__init__(target = self.main, name = _name)
        self.personal = []


    def main(self):
        print("Cocina encendida")

class CocinaQuesadillero():
    pass



if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, filename="logfile.log", filemode="a+",
                    format="%(asctime)-15s %(levelname)-8s %(message)s")
    print("Scheduler test 1")
    Cocina = CocinaTaqueros("Taqueros")
    Cocina.start()
    Cocina.personal.append(PersonalTaqueria("Omar"))
    Cocina.personal[0].start()

    while(True):
        logging.info("Escriba la cantidad de unidades que tiene este indice: \n")
        orden = None
        try:
            orden = int(input())
        except:
            print('Exception for tacos input')
        print(f'Hay {orden} de unidades')
        Cocina.personal[0].queue.put(orden)
    
    #x = 5
    #print(getTime())
