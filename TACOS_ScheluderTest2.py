import multiprocessing
from queue import Empty
import threading
import logging
import datetime
import string
import time
import json
import emoji
from time import sleep
import sys
abcdario = list(string.ascii_uppercase)
debug_state = True

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
        self.StarvingTaxerThread = threading.Thread(
            target=self.starvingTaxer,
            args=()
        )
        self.emojis=''
        self.ordersPerSecondDelta = 3  # ^-1
        self.cookUnitDelta = 0.5  # Minimo para cocinar
        self.Rescheduling = False
        self.Cooking = False
        self.cuadernilloRecibidos = {} #Cuaderno con los jsons de entrada
        self.cuadernilloSalidas = {} # Cuadrerno con los jsons de salida
        self.ordenes = {}  # dict in mind per worker
        self.ordenesHeads = []  # lista con las cabezas de subordenenes
        self.tacoCounter = 0
        self.orderCounter = 0
        self.stackCounter = 0 #Antes conocido como tacoCounter (incorrectamente)
        self.constMagnitud = 40  # p90 redondeado, muy grande = hacer parte
        self.constStarving = 0.01  # blah blah + [utis*const*tiempoatrasado]
        self.shortestOrderIndex = None  # Una vez inicia un stack no lo detiene

    def main(self):
        # Formato de prueba
        #  Orden  = (tiempollegada,duracionOrden)
        print(f"Taquero {self.name} en linea")
        self.OrderRecieverThread.start()
        #self.CookerThread.start()
        #self.StarvingTaxerThread.start()

    def taquitos_emojis(self):
        print(f"ORDENES:",end='')
        self.emojis=':taco: ' * len(self.ordenes)
        print(emoji.emojize(self.emojis))
        self.emojis = ''

    def SplitOrder(self, orden):
        pedido = orden
        numSuborden = 0
        #Seccionar en partes la orden (los indices de ['orden'])
        for subOrden in pedido['orden']:
            costoUTIs = 1
            tiempoParaCocinar  = 0
            if(subOrden['type'] == 'taco'):
                #Hacer un calculo del costo
                if('salsa' in subOrden['ingredients']):
                    costoUTIs += 2.66667
                    tiempoParaCocinar += 0.5
                if('guacamole' in subOrden['ingredients']):
                    costoUTIs += 3.5
                    tiempoParaCocinar += 0.5
                if('cilantro' in subOrden['ingredients']):
                    costoUTIs += 2
                    tiempoParaCocinar += 0.5
                if('cebolla' in subOrden['ingredients']):
                    costoUTIs += 2
                    tiempoParaCocinar += 0.5
                #costo es costo por taco * cantidadtacos
                #Costo individual servirá para la división de sstacks
                costoUTIsIndividual = costoUTIs
                costoUTIs = costoUTIs * subOrden['quantity']
                ## Fin del calculo del costo
                if(costoUTIs < self.constMagnitud):
                    #No dividir, solo 1 stack por esta suborden
                    prioridad = ((costoUTIs**-1)*10)
                    subSplitIndex = 0
                    self.ordenes[str(self.stackCounter)] = [
                        costoUTIs,
                        prioridad,
                        (self.orderCounter, numSuborden, subSplitIndex),
                        time.time(),
                        subOrden['quantity'],
                        costoUTIsIndividual
                    ]
                    logging.info(
                        f"Stack {self.stackCounter} has ben put in head")
                    subSplitIndex += 1
                    self.stackCounter += 1  
                    pass
                else:
                    #Dividir orden en partes (stacks)
                    #Primero ver cuantos stacks puedo hacer
                    #numStacks = costoUTIs // self.constMagnitud
                    tacosPorStack =  self.constMagnitud // costoUTIsIndividual
                    numStacks = subOrden['quantity'] // tacosPorStack
                    #calcular tacos sobrantes
                    tacosSobrantes =  subOrden['quantity'] - (
                        tacosPorStack * numStacks
                    )
                    residuoUTIS = costoUTIsIndividual * tacosSobrantes
                    if(numStacks == 1):
                        #Pasar el taco sobrante al stack cola si solo
                        #  hay 1 stack y su cola,
                        tacosSobrantes = 1
                        tacosPorStack -=1 
                    #Como habia hecho en el test2 inician
                    # primero vá la cola
                    # Si hubo residuo hay una "cola" para evitar problemas
                    # primero metamos a la cola la cabeza y que sus subse
                    # -cuenters grandes stacks sean vecinos
                    # Consultar con Omar para sus apuntes de estas lineas
                    ## Si hubo residuo ponemos cola, si no entonces no
                    if(residuoUTIS > 0):
                        prioridad = ((residuoUTIS**-1)*10)
                        subSplitIndex = 0
                        self.ordenes[str(self.stackCounter)] = [
                            residuoUTIS,
                            prioridad,
                            (self.orderCounter, numSuborden, subSplitIndex),
                            time.time(),
                            tacosSobrantes,
                            costoUTIsIndividual
                        ]
                        logging.info(
                            f"Stack {self.stackCounter} has ben put in head")
                        #subSplitIndex += 1
                        self.stackCounter += 1                  
                    for numStack in range(int(numStacks)):
                        costoStack = tacosPorStack * costoUTIsIndividual
                        prioridad = ((costoStack**-1)*10)
                        self.ordenes[str(self.stackCounter)] = [
                            costoStack,
                            prioridad,
                            (self.orderCounter, numSuborden, numStack),
                            time.time(),
                            tacosPorStack,
                            costoUTIsIndividual
                        ]
                        logging.info(
                            f"Stack {self.stackCounter} has ben put in head")
                        #subSplitIndex += 1
                        self.stackCounter += 1   
                        pass
                    #Este bug ya no es necesario parchearlo así
                    # porque ahora estoy usando for y no while (creo..)
                    #self.stackCounter -=1
                    pass
                pass
            pass
            numSuborden += 1
        pass
    
    
    def recieveClientOrders(self):
        while(True):
            if debug_state == True:
                for key in self.ordenes:
                    print(f"\nOrder:{key} || ",end='')
                    for v_data in self.ordenes[key]:
                        if isinstance(v_data, float):
                            print(f"{round(v_data,2)} ",end='') 
                        else:
                            print(f"{v_data} ",end='')

                print(f'HeadsofOrders:{self.ordenesHeads}')
                logging.info(self.ordenes)     
            else:
                self.taquitos_emojis()
                                  
            if(self.queue.empty()):
                pass
            else:
                newOrder = self.queue.get_nowait()
                self.cuadernilloRecibidos[str(self.tacoCounter)] = newOrder
                logging.info("Iniciando particion de orden x")
                self.SplitOrder(newOrder)
                logging.info("Finalizada la particion de orden x")
                # subSplitIndex = 0
                # self.tacoCounter += 1
                # if(newOrder > self.constMagnitud):
                #     # Idea: dividir en stacks (no la estructura)
                #     # las ordenes que excedan x tacos
                #     # y que se respete el orden de UTIS 1ro y si hay empate
                #     # se hace por FCFS
                #     remainingUnits = newOrder
                #     ogTacoCounter = self.tacoCounter
                #     prioridad = ((self.constMagnitud**-1)*10)
                #     self.ordenesHeads.append(ogTacoCounter)
                #     utisResidue = newOrder % self.constMagnitud
                #     if(utisResidue > 0):
                #         # Si hubo residuo hay una "cola" para evitar problemas
                #         # primero metamos a la cola la cabeza y que sus subse
                #         # -cuenters grandes stacks sean vecinos
                #         prioridad = ((utisResidue**-1)*10)
                #         self.ordenes[str(self.tacoCounter)] = [
                #             utisResidue,
                #             prioridad,
                #             (ogTacoCounter, subSplitIndex),
                #             time.time()
                #         ]
                #         logging.info(
                #             f"Stack {self.tacoCounter} has ben put in head")
                #         subSplitIndex += 1
                #         self.tacoCounter += 1
                #         remainingUnits -= utisResidue
                #     while(remainingUnits >= self.constMagnitud):
                #         prioridad = ((self.constMagnitud**-1)*10)
                #         self.ordenes[str(self.tacoCounter)] = [
                #             self.constMagnitud,
                #             prioridad,
                #             (ogTacoCounter, subSplitIndex),
                #             time.time()
                #         ]
                #         logging.info(
                #             f"Stack {self.tacoCounter} has ben put in head")
                #         subSplitIndex += 1
                #         remainingUnits -= self.constMagnitud
                #         self.tacoCounter += 1
                #         if(remainingUnits == 0):
                #             self.tacoCounter -= 1  # Quitar el que sobra
                #     pass
                # else:
                #     prioridad = ((newOrder**-1)*10)
                #     self.ordenesHeads.append(self.tacoCounter)
                #     self.ordenes[str(self.tacoCounter)] = [
                #         newOrder,
                #         prioridad,
                #         (self.tacoCounter, subSplitIndex),
                #         time.time()
                #     ]
                #     logging.info(
                #         f"Stack {self.tacoCounter} has ben put in head")
                try:
                    self.Rescheduling = True
                    #self.sortOrders()
                    self.Rescheduling = False
                except Exception as e:
                    logging.exception(f"Error -> {Exception}")
                    pass
            #if debug_state is True:
            time.sleep(self.ordersPerSecondDelta)

    def cook(self):
        while(True):
            if(bool(self.ordenes)):
                self.Cooking = True
                if(self.shortestOrderIndex == None):
                    # Sí actualmente no trabaja en un stack, darle el indice
                    # TODO referirlo como biggestPriorityIndex
                    # Sacada respuesta de
                    # https://stackoverflow.com/a/64152259 por Sloper C. (2020)
                    # el key 0 es de la lista hecha diccionario con la prioridad
                    # $  mas grande
                    self.shortestOrderIndex = str(list(self.ordenes.keys())[0])
                    logging.info(
                        f"Stack {self.shortestOrderIndex} assigned to work at")
                else:
                    # Si no que siga trabajando con ese stack incluso si
                    # llega a haber un sort nuevo con orden más chica
                    pass
                # La delta ahora se hace primero para evitar reporte
                # prematura de completicion de stack
                #if debug_state is True:
                time.sleep(self.cookUnitDelta)
                if(not self.Rescheduling):
                    # Si no estamos reordenando podemos cocinar
                    if self.ordenes[self.shortestOrderIndex][0] > 0:
                        self.ordenes[str(self.shortestOrderIndex)
                                     ][0] -= self.cookUnitDelta
                        # resta el costo del taco hecho
                        if(self.ordenes[self.shortestOrderIndex][0] == 0):
                            # Remover de las ordenes cabeza
                            # Poner la nueva cabeza si es necesario
                            # y hacerle pop del diccionario de stacks/ordenes
                            if(str(int(self.shortestOrderIndex)+1) in self.ordenes):
                                # primero revisar si hay un taco counter subsecuente
                                # Si se acabo el ultimo stack no hya porque revisar que exista
                                # un sucesor
                                if(self.ordenes[str(int(self.shortestOrderIndex)+1)][2][0]
                                   == self.ordenes[self.shortestOrderIndex][2][0]):
                                    # Sí el siguiente taco counter comparte el mismo
                                    # padre/inicio entonces hacer el venico la nueva
                                    # cabeza al acabar este stack
                                    self.ordenesHeads.remove(
                                        int(self.shortestOrderIndex))
                                    self.ordenesHeads.append(
                                        int(self.shortestOrderIndex)+1)
                                else:
                                    # Si no tiene vecinos hermanos entonces solo quitar
                                    self.ordenesHeads.remove(
                                        int(self.shortestOrderIndex))
                            else:
                                # Si el ultimo elemento cocinado (en algun insante)
                                # era una cabeza que no pudo ser removida, la
                                # intentamos quitar
                                if(int(self.shortestOrderIndex) in self.ordenesHeads):
                                    self.ordenesHeads.remove(
                                        int(self.shortestOrderIndex))
                            # Una vez acabado el proceso le hacemos pop
                            # saca orden del taquero
                            self.ordenes.pop(self.shortestOrderIndex, None)
                            logging.info(
                                f"Stack {self.shortestOrderIndex} completed")
                            
                            self.shortestOrderIndex = None
            else:
                self.Cooking = False

    def starvingTaxer(self):
        while(True):
            # Link para explicación gráfica de los impuestos
            # https://www.desmos.com/calculator/ksquctjgyz
            # Siempre estar dando impuestos a las cabezas cada segundo y haciendo
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
            if debug_state is True:
                time.sleep(1.0)

    def sortOrders(self):
        logging.info("Sorting start")
        # Primero sortear por desempate FCFS (se hace esto primero desempate y luego el bueno)
        sortedOrders = sorted(self.ordenes.items(),
                              key=lambda item: item[1][3])
        # Luego sortear por pioridad donde mas es mas importante
        # Basado en esta respuesta de stack overflow
        # https://stackoverflow.com/questions/18414995/how-can-i-sort-tuples-by-reverse-yet-breaking-ties-non-reverse-python/18415853#18415853
        sortedOrders = sorted(self.ordenes.items(),
                              key=lambda item: item[1][1], reverse=True)
        self.ordenes = dict(sortedOrders)
        logging.info("Sorting end")
        pass


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
    #Solo poner estas ordenes mientras hacemos pruebas
    ordersToTest = 2
    logging.basicConfig(level=logging.DEBUG, filename="logfile.log", filemode="a+",
                        format="%(asctime)-15s %(levelname)-8s %(message)s")
    print("Scheduler test 1")
    Cocina = CocinaTaqueros("Taqueros")
    Cocina.start()
    Cocina.IngresoPersonal(Cocina)

    while(True):
        with open("jsons.json") as OrdenesJSON:
            ListadoOrdenes = json.load(OrdenesJSON)
            for i in range(ordersToTest):
                orden = ListadoOrdenes[i]
                Cocina.personal[0].queue.put(orden)

