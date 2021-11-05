import multiprocessing
import threading
import logging
import datetime
import string
import time

abcdario = list(string.ascii_uppercase)

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
        self.StarvingTaxerThread = threading.Thread(
            target = self.starvingTaxer,
            args = ()
        )
        self.ordersPerSecondDelta = 3 #^-1 
        self.cookUnitDelta = 0.5 #Minimo para cocinar
        self.Rescheduling = False
        self.Cooking = False
        self.ordenes = {} #dict in mind per worker
        self.tacoCounter = 0
        self.constMagnitud = 12 #p90 redondeado, muy grande = hacer parte
        self.constStarving = 0.01 # blah blah + [utis*const*tiempoatrasado]


    def main(self):
        # Formato de prueba
        #  Orden  = (tiempollegada,duracionOrden)
        print(f"Taquero {self.name} en linea")
        self.OrderRecieverThread.start()
        #self.CookerThread.start()


    def recieveClientOrders(self):
        while(True):
            print(f"{self.ordenes}")
            logging.info(self.ordenes)
            try:
                newOrder = self.queue.get_nowait()
                subSplitIndex = 0
                self.tacoCounter += 1
                if(newOrder > self.constMagnitud):
                    #Idea: dividir en stacks (no la estructura)
                    # las ordenes que excedan x tacos
                    # y que se respete el orden de UTIS 1ro y si hay empate
                    # se hace por FCFS
                    remainingUnits  = newOrder
                    ogTacoCounter = self.tacoCounter
                    prioridad = ((self.constMagnitud**-1)*10)
                    while(remainingUnits > self.constMagnitud):
                        self.ordenes[str(self.tacoCounter)] = [
                            self.constMagnitud, 
                            prioridad,
                            0, #numOfDeltasthat have ocurred
                            f"{ogTacoCounter}-{subSplitIndex}",
                            time.time()
                        ]
                        self.tacoCounter += 1
                        subSplitIndex  += 1
                        remainingUnits -= self.constMagnitud

                    prioridad = ((remainingUnits**-1)*10)
                    self.ordenes[str(self.tacoCounter)] = [
                        remainingUnits, 
                        prioridad,
                        0, #numOfDeltasthat have ocurred
                        f"{ogTacoCounter}-{subSplitIndex}",
                        time.time()
                    ]
                    
                else:
                    prioridad = ((newOrder**-1)*10)
                    self.ordenes[str(self.tacoCounter)] = [
                        newOrder, 
                        prioridad,
                        0, #numOfDeltas that have ocurred
                        f"{self.tacoCounter}-{subSplitIndex}",
                        time.time()
                    ]
                self.Rescheduling = True
                self.sortOrders()
                self.Rescheduling = False
            except:
                pass
            time.sleep(self.ordersPerSecondDelta)
    
    def cook(self):
        while(True):
            if(bool(self.ordenes)): 
                self.Cooking = True  
                try: 
                    shortestOrderIndex = min(self.ordenes, key=self.ordenes.get) 
                    #orden mas corta en el self.orden
                    if self.ordenes[shortestOrderIndex][0] > 0 and (not self.Rescheduling):
                        self.ordenes[str(shortestOrderIndex)][0] -= self.cookUnitDelta 
                        #resta el costo del taco hecho
                    else:
                        self.ordenes.pop(shortestOrderIndex,None) #saca orden del taquero
                        logging.info(f"Order {shortestOrderIndex} completed")
                    time.sleep(self.cookUnitDelta)            
                except:
                    pass
            else:
                self.Cooking = False
    
    def starvingTaxer(self):
        while(True):
            if(self.Cooking):
                
        pass


    def sortOrders(self):
        self.ordenes = dict(sorted(self.ordenes.items(), key=lambda item: item[1][1])[::-1])
        pass




class CocinaTaqueros(multiprocessing.Process):
    def __init__(self,_name):
        #SuperConsteructor
        super(CocinaTaqueros, self).__init__(target = self.main, name = _name)
        self.personal = []

    def main(self):
        print("Cocina encendida")


    def IngresoPersonal(self,cocina):
        cocina.personal.append(PersonalTaqueria("Omar"))
        cocina.personal[0].start()



class CocinaQuesadillero():
    pass



if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, filename="logfile.log", filemode="a+",
                    format="%(asctime)-15s %(levelname)-8s %(message)s")
    print("Scheduler test 1")
    Cocina = CocinaTaqueros("Taqueros")
    Cocina.start()
    Cocina.IngresoPersonal(Cocina)


    while(True):
        logging.info("Escriba la cantidad de unidades que tiene este indice: \n")
        orden = None
        try:
            orden = int(input())
        except:
            print('Exception for tacos input')
        Cocina.personal[0].queue.put(orden)
    
