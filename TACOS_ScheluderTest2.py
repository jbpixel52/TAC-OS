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
        self.ordenesHeads = [] #lista con las cabezas de subordenenes
        self.tacoCounter = 0
        self.constMagnitud = 12 #p90 redondeado, muy grande = hacer parte
        self.constStarving = 0.01 # blah blah + [utis*const*tiempoatrasado]
        self.shortestOrderIndex = None #Una vez inicia un stack no lo detiene


    def main(self):
        # Formato de prueba
        #  Orden  = (tiempollegada,duracionOrden)
        print(f"Taquero {self.name} en linea")
        self.OrderRecieverThread.start()
        self.CookerThread.start()
        self.StarvingTaxerThread.start()


    def recieveClientOrders(self):
        while(True):
            print(f"{self.ordenes}")
            print(self.ordenesHeads)
            logging.info(self.ordenes)
            if(self.queue.empty()):
                pass
            else:
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
                    self.ordenesHeads.append(ogTacoCounter)
                    utisResidue = newOrder % self.constMagnitud
                    if(utisResidue > 0):
                        #Si hubo residuo hay una "cola" para evitar problemas
                        # primero metamos a la cola la cabeza y que sus subse
                        # -cuenters grandes stacks sean vecinos
                        prioridad = ((utisResidue**-1)*10)
                        self.ordenes[str(self.tacoCounter)] = [
                                utisResidue, 
                                prioridad,
                                (ogTacoCounter,subSplitIndex),
                                time.time()
                        ]
                        logging.info(f"Stack {self.tacoCounter} has ben put in head")
                        subSplitIndex += 1
                        self.tacoCounter += 1 
                        remainingUnits -= utisResidue
                    while(remainingUnits >= self.constMagnitud):
                        prioridad = ((self.constMagnitud**-1)*10)
                        self.ordenes[str(self.tacoCounter)] = [
                            self.constMagnitud, 
                            prioridad,
                            (ogTacoCounter,subSplitIndex),
                            time.time()
                        ]
                        logging.info(f"Stack {self.tacoCounter} has ben put in head")
                        subSplitIndex  += 1
                        remainingUnits -= self.constMagnitud
                        self.tacoCounter +=1
                        if(remainingUnits == 0):
                            self.tacoCounter -= 1 #Quitar el que sobra
                    pass 
                else:
                    prioridad = ((newOrder**-1)*10)
                    self.ordenesHeads.append(self.tacoCounter)
                    self.ordenes[str(self.tacoCounter)] = [
                        newOrder, 
                        prioridad,
                        (self.tacoCounter,subSplitIndex),
                        time.time()
                    ]
                    logging.info(f"Stack {self.tacoCounter} has ben put in head")
                try:
                    self.Rescheduling = True
                    self.sortOrders()
                    self.Rescheduling = False
                except Exception as e:
                    logging.exception(f"Error -> {Exception}")
                    pass
            time.sleep(self.ordersPerSecondDelta)
    

    def cook(self):
        while(True):
            if(bool(self.ordenes)): 
                self.Cooking = True  
                if(self.shortestOrderIndex == None):
                    #Sí actualmente no trabaja en un stack, darle el indice
                    #TODO referirlo como biggestPriorityIndex
                    #Sacada respuesta de 
                    # https://stackoverflow.com/a/64152259 por Sloper C. (2020)
                    # el key 0 es de la lista hecha diccionario con la prioridad
                    #$  mas grande
                    self.shortestOrderIndex = str(list(self.ordenes.keys())[0])
                    logging.info(f"Stack {self.shortestOrderIndex} assigned to work at")
                else:
                    #Si no que siga trabajando con ese stack incluso si 
                    #llega a haber un sort nuevo con orden más chica
                    pass
                #La delta ahora se hace primero para evitar reporte
                # prematura de completicion de stack
                time.sleep(self.cookUnitDelta)
                if(not self.Rescheduling):
                    #Si no estamos reordenando podemos cocinar
                    if self.ordenes[self.shortestOrderIndex][0] > 0:
                        self.ordenes[str(self.shortestOrderIndex)][0] -= self.cookUnitDelta 
                        #resta el costo del taco hecho
                        if(self.ordenes[self.shortestOrderIndex][0] == 0):
                            #Remover de las ordenes cabeza
                            # Poner la nueva cabeza si es necesario
                            # y hacerle pop del diccionario de stacks/ordenes
                            if(str(int(self.shortestOrderIndex)+1) in self.ordenes):
                                #primero revisar si hay un taco counter subsecuente
                                #Si se acabo el ultimo stack no hya porque revisar que exista
                                # un sucesor
                                if(self.ordenes[str(int(self.shortestOrderIndex)+1)][2][0] 
                                == self.ordenes[self.shortestOrderIndex][2][0]):
                                    #Sí el siguiente taco counter comparte el mismo
                                    # padre/inicio entonces hacer el venico la nueva 
                                    # cabeza al acabar este stack
                                    self.ordenesHeads.remove(int(self.shortestOrderIndex))
                                    self.ordenesHeads.append(int(self.shortestOrderIndex)+1)
                                else:
                                    #Si no tiene vecinos hermanos entonces solo quitar
                                    self.ordenesHeads.remove(int(self.shortestOrderIndex))
                            else:
                                #Si el ultimo elemento cocinado (en algun insante)
                                # era una cabeza que no pudo ser removida, la 
                                # intentamos quitar    
                                if(int(self.shortestOrderIndex) in self.ordenesHeads):
                                    self.ordenesHeads.remove(int(self.shortestOrderIndex)) 
                            # Una vez acabado el proceso le hacemos pop
                            self.ordenes.pop(self.shortestOrderIndex,None) #saca orden del taquero
                            logging.info(f"Stack {self.shortestOrderIndex} completed") 
                            self.shortestOrderIndex = None         
            else:
                self.Cooking = False
            
    

    def starvingTaxer(self):
        while(True):
            #Link para explicación gráfica de los impuestos 
            # https://www.desmos.com/calculator/ksquctjgyz
            #Siempre estar dando impuestos a las cabezas cada segundo y haciendo
            # sort ¿tardá mucho? ya veremos jesjes
            for headIndex in self.ordenesHeads:
                UTIs = self.ordenes[str(headIndex)][0]
                base = (UTIs ** -1) * 10
                tax = (
                        UTIs
                        * self.constStarving 
                        * (time.time() - self.ordenes[str(headIndex)][3])
                    )
                self.ordenes[str(headIndex)][1] = (base + tax)
            logging.info("Taxer will sort")
            self.sortOrders()
            logging.info("Taxer has sorted")
            time.sleep(1.0)



    def sortOrders(self):
        logging.info("Sorting start")
        #Primero sortear por desempate FCFS (se hace esto primero desempate y luego el bueno)
        sortedOrders = sorted(self.ordenes.items(), key=lambda item: item[1][3])
        #Luego sortear por pioridad donde mas es mas importante
        # Basado en esta respuesta de stack overflow
        # https://stackoverflow.com/questions/18414995/how-can-i-sort-tuples-by-reverse-yet-breaking-ties-non-reverse-python/18415853#18415853
        sortedOrders = sorted(self.ordenes.items(), key=lambda item: item[1][1], reverse=True)
        self.ordenes = dict(sortedOrders)
        logging.info("Sorting end")
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
        orden = None
        try:
            orden = int(input())
            Cocina.personal[0].queue.put(orden)
        except:
            print('Exception for tacos input')