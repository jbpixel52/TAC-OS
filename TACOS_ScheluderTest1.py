# %%
import multiprocessing
import threading
import logging
import datetime
import time

tacokillcount=0

def getTime():
    LocalTime = datetime.datetime.now().strftime("%H:%M:%S")
    return LocalTime


class PersonalTaqueria(threading.Thread):
    def __init__(self, nombre):
        # SuperConstructor
        super(PersonalTaqueria, self).__init__(target=self.main, name=nombre)
        self.queue = multiprocessing.Queue()
        self.OrderRecieverThread = threading.Thread(
            target=self.recieveClientOrders,
            args=()
        )
        self.CookerThread = threading.Thread(
            target=self.cook,
            args=()
        )
        self.ordersPerSecondDelta = 3  # ^-1
        self.cookUnitDelta = 0.5  # Minimo para cocinar
        self.Rescheduling = False
        self.ordenes = {}  # dict in mind per worker
        self.tacoCounter = 0
        self.constMagnitud = 12  # p90 redondeado, muy grande = hacer parte

    def main(self):
        # Formato de prueba
        #  Orden  = (tiempollegada,duracionOrden)
        print(f"Taquero {self.name} en linea")
        self.OrderRecieverThread.start()
        self.CookerThread.start()

    def recieveClientOrders(self):
        while(True):
            
            logging.info(self.ordenes)
            try:
                newOrder = self.queue.get_nowait()
                subSplitIndex = 0  # Index
                self.tacoCounter += 1
                if(newOrder > self.constMagnitud):
                    # Idea: dividir en stacks (no la estructura)
                    # las ordenes que excedan var:constMagnitud tacos
                    # y que se respete el orden de UTIS 1ro y si hay empate
                    # se hace por FCFS
                    remainingUnits = newOrder
                    ogTacoCounter = self.tacoCounter
                    while(remainingUnits > self.constMagnitud):
                        self.ordenes[str(self.tacoCounter)] = [
                            self.constMagnitud,
                            f"{ogTacoCounter}-{subSplitIndex}",
                            time.time()
                        ]
                        self.tacoCounter += 1
                        subSplitIndex += 1
                        remainingUnits -= self.constMagnitud

                    self.ordenes[str(self.tacoCounter)] = [
                        remainingUnits,
                        f"{ogTacoCounter}-{subSplitIndex}",
                        time.time()
                    ]

                else:  # esto es si la orden no sobrepasa el treshold
                    self.ordenes[str(self.tacoCounter)] = [
                        newOrder,
                        f"{self.tacoCounter}-{subSplitIndex}",
                        time.time()
                    ]
                self.Rescheduling = True
                self.sortOrders()
                self.Rescheduling = False
            except:
                pass
            print(f"{self.ordenes}")
            time.sleep(self.ordersPerSecondDelta)

    def cook(self):
        while(True):
            try:
                shortestOrderIndex = min(self.ordenes, key=self.ordenes.get)
                # orden mas corta en el self.orden
                if(not self.Rescheduling):
                    if self.ordenes[shortestOrderIndex][0] > 0:
                        self.ordenes[str(shortestOrderIndex)
                                    ][0] -= self.cookUnitDelta
                        # resta el costo del taco hecho
                    else:
                        # saca orden del taquero
                        self.ordenes.pop(shortestOrderIndex, None)
                        logging.info(f"{shortestOrderIndex} Cocinado!")
                        print(f"{shortestOrderIndex} Cocinado!")
                        tacokillcount=+1
                    time.sleep(self.cookUnitDelta)
                    pass
            except:
                pass

    def sortOrders(self):
        print('Sorting Ordenes')
        # Sorted de python usa TimSort, time complexity O(n log n)
        # Space complexity Omega(n)
        self.ordenes = dict(sorted(self.ordenes.items(),
                            key=lambda item: item[1][0]))
        temp_index=0
        for orden_info in self.ordenes.values():
            temp_index+=1
            self.get_starving_treshold(orden=orden_info,index=temp_index)
        temp_index=0            

    def get_starving_treshold(self,orden,index):
        waiting_time = int(time.time()-orden[2])
        utis = orden[0] #example value
        order_is_split=True #determine if its a suborder
        wait_twice = 1
        wait_twice +=1 if order_is_split else 0
        starving_treshold = utis * wait_twice
        
        if waiting_time > starving_treshold:
            print('I WANT TO TALK TO THE MANAGER. MY ORDER IS LATE!')
            #reordering time
            # Swapping Values for the given positions... 
            tupList = list(self.ordenes.items())
            tupList[self.get_unlucky_index(index)], tupList[index] = tupList[index], tupList[self.get_unlucky_index(index)]
            swappedOders = dict(tupList)

            # Printing the dictionaries...
            print("Initial dictionary = ", end = " ")
            print(tupList)
            print("Dictionary after swapping = ", end = " ")
            print(swappedOders)

    def get_unlucky_index(self,index_starved):
        return int((len(self.ordenes)-index_starved)/2)


class CocinaTaqueros(multiprocessing.Process):
    def __init__(self, _name):
        # SuperConsteructor
        super(CocinaTaqueros, self).__init__(target=self.main, name=_name)
        self.personal = []

    def main(self):
        print("Cocina encendida")

    def IngresoPersonal(self, cocina):
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
        logging.info(
            "Escriba la cantidad de unidades que tiene este indice: \n")
        orden = None
        try:
            orden = int(input())
        except:
            print('Exception for tacos input')
        Cocina.personal[0].queue.put(orden)
