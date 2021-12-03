import copy
import datetime
import json
import logging
import multiprocessing
import queue
import string
import sys
import threading
import time
from queue import Empty, PriorityQueue, Queue
from time import sleep
from datetime import datetime


abcdario = list(string.ascii_uppercase)
debug_state = True



def getTime():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')


class PersonalTaqueria(threading.Thread):
    def __init__(self, _name):
        # SuperConstructor
        super(PersonalTaqueria, self).__init__(target=self.main, name=_name)
        self.queue = multiprocessing.Queue()
        self.OrderRecieverThread = threading.Thread(
            target=self.recieveOrders,
            args=(),
            name=f"{self.name}'s Window"
        )
        self.CookerThread = threading.Thread(
            target=self.cook,
            args=(),
            name=f"{self.name}'s stove"
        )
        self.StarvingTaxerThread = threading.Thread(
            target=self.starvingTaxer,
            args=(),
            name=f"{self.name}'s Taxer"
        )
        self.FanThread = threading.Thread(
            target=self.fanChecker,
            args=(),
            name=f"{self.name}'s Fan"
        )
        self.saving_memory = threading.Thread(
            target=self.staff_to_json,
            args=(),
            name=f"{self.name}'s Dash communicator"
        )

        self.emojis = ''
        # Variables de pertnenencia
        self.ID = None
        self.meatTypes = None # Lo asigna Cocina
        self.allowedOrderTypes = ["taco","quesadilla"]
        self.allowedMeatTypes = ["suadero",
                                 "adobada", "asada", "cabeza", "tripa"]
        self.cocinaDirectory = {
            "adoaba": 0,
            "asada": 1,
            "suadero": 1,
            "unused": 2,
            "tripa": 3,
            "cabeza": 3
        }
        # Queues de mandar pedidos o recibir pedidos no correspondientes
        self.sendQueues = []
        self.recieveQueue = Queue()
        # Queues de mandar o recibir pedidos no correspondientes hechos
        self.sendQueuesReturn = []
        self.recieveQueueReturn = Queue()
        # Variables MUTEX
        self.Splitting = False
        self.Rescheduling = False
        self.Cooking = False
        # Esctructuras de datos y cosas del output
        self.jsonOutputTemplate = None  # Se asigna en main
        self.hasCookedSomething = False
        self.jsonOutputs = {}  # Cuadrerno con los jsons de salida
        self.ordenes = {}  # dict in mind per worker
        self.ordenesHeads = []  # lista con las cabezas de subordenenes
        self.ordenesSuborders = {}  # Dict con listas de listas sobordenes
        self.ordersThatAreNotMine = [] # Lista de indices de ordenes (son subs en realidad) no pertenecientes
        # Variables Delta
        self.ordersPerSecondDelta = 3  # ^-1
        self.cookUnitDelta = 0.5  # Minimo para cocinar
        self.deltasPerTaco = 0  # Definida por el thread cooker, varia por stack
        # La quadfecta de las variables counter
        self.tacoCounter = 0
        self.stackCounter = 0
        self.stackCounterCompleted = 0  # stackCounter ya era usada para registro
        self.subOrderCounter = 0
        self.orderCounter = 0
        self.orderCounterCompleted = 0  # tambien ya era usada para registros
        # Constantes relevantes
        self.constMagnitud = 40  # ya no es p90 lol, ni para 4 tacos con todo alcanzaba
        # blah blah + [utis*const*tiempoatrasado], consultar desmos para demo
        self.constStarving = 0.005
        # Variables de que se está trabajando ahorita, stack, sub y orden
        self.shortestOrderIndex = None  # Una vez inicia un stack no lo detiene
        self.currentWorkingSuborder = None
        self.currentWorkingOrder = None
        self.currentWorkingStack = None
        # Variables de chaches de ingredientes, una es Maximo y otra es cuantas quedan
        self.maxTortillas = 50
        self.currentTortillas = 50
        self.maxSalsa = 150
        self.currentSalsa = 150
        self.maxGuacamole = 100
        self.currentGuacamole = 100
        self.maxCilantro = 200
        self.currentCilantro = 200
        self.maxCebolla = 200
        self.currentCebolla = 200
        self.currentIngridientList = []
        # Variables relacionadas con el request de ingredientes
        self.thresholdOfCilantroAndCebollaRequest = 0.70
        self.thresholdOfSalsaRequest = 0.65
        self.thresholdOfGuacamoleRequest = 0.80
        self.tortillaRequestBoost = 0.25
        # Para razones de comparativa de estancamiento, existe ingredientes infinitos
        self.infiniteIngridients = False
        # Chalan asignado, lo asigna la clase cocina
        self.chalanAsignado = None
        # Lista de variables que especifican que ya se solicitó un rellenado
        #  de ingredientes, el chalan se encarga de quitarlos de tal lista
        self.listOfRquestedIngridients = []
        # Variables del ventilador
        self.isFanActive = False
        self.fanThreshold = 32  # Default es 600 pero debo probarlo pequeño antes
        self.useTimeOfFan = 60  # tiempo que se usa el ventilador
        # Variables del descanso, definen el tiempo que se descanza cada x Tacos
        self.isResting = False
        self.tacosRestingThreshold = 50  # Default es 1000
        self.maxRestingTime = 30  # Maximo que puede descansar de una sentada
        #   Solo se baja este V cuando hay hangups de ingredientes
        self.remainingRestingTime = self.maxRestingTime
        self.isAnOwl = False  # Si es true no necesita dormir

    def staff_to_json(self):
        while True:
            sleep(5)  # HERE WE SET THE SAVING TO DISK INTERVAL e.g., 3 seconds < -
            print(f"- > saving {self.name} at {getTime()} ...")
            self.objects_to_json()

    def objects_to_json(self):
        path = 'logs/staff/taqueros/'+self.name+'.json'
        with open(path, mode='w', encoding='utf-8') as file:
            serialized = {'name': self.name, 'ID': self.ID, 'ordenes': self.ordenes, 'stackcounter': self.stackCounter,
                          'isFanActive': self.isFanActive, 'chalan': self.chalanAsignado.name, 'cooking': self.Cooking, 'resting': self.isResting, 'Owl': self.isAnOwl,
                          'currentTortillas': self.currentTortillas, 'currentCebolla': self.currentCebolla, 'currentCilantro': self.currentCilantro, 'currentSalsa': self.currentSalsa, 'currentGuacamole': self.currentGuacamole, 'currentWorkingOrder': self.currentWorkingOrder, 'currentWorkingSuborder': self.currentWorkingSuborder}
            json.dump(serialized, file, indent=4, sort_keys=True)
            file.close()

    def main(self):
        # Decir que se está en linea
        print(f"Taquero {self.name} en linea")
        # Hacer el templete del output de salidas
        with open("outputTemplate.json") as jsonSalida:
            self.jsonOutputTemplate = json.load(jsonSalida)

        self.OrderRecieverThread.start()
        self.CookerThread.start()
        self.StarvingTaxerThread.start()
        self.FanThread.start()
        self.saving_memory.start()

    def startOutputtingOrder(self, orden):
        # Funcion que crea un indice en los outputs de salidas
        #  lo hace en base al templete lul
        ordenID = orden['request_id']
        logging.info(f"{self.ID} is outputting input of {ordenID}")
        # condenado seas python y tu inabilidad de copiar cosas por valor al 100%
        copia = copy.deepcopy(self.jsonOutputTemplate["orderIDGoesHere"])
        self.jsonOutputs[ordenID] = copia
        # Variable que apoya al retorno de ordenes no correspondientes
        if(self.orderCounter not in self.ordersThatAreNotMine):
            self.jsonOutputs[ordenID]["responsable_orden"] = self.ID
        else:
            self.jsonOutputs[ordenID]['responsable_orden'] = orden["responsable_orden"]
        self.jsonOutputs[ordenID]['request_id'] = ordenID
        self.jsonOutputs[ordenID]['orden'] = orden['orden']
        self.jsonOutputs[ordenID]['datetime'] = orden['datetime']
        self.jsonOutputs[ordenID]['status'] = orden['status']
        # Reportar el momento de inicio
        self.jsonOutputs[ordenID]['answer']['start_time'] = getTime()
        self.jsonOutputs[ordenID]['answer']['end_time'] = 0
        # Reportar el primer paso que es esperar a que se cocine
        # for i in subordenes
        for suborden in range(len(orden['orden'])):
            # Crear slots para pasos si es que son mayores a 0
            if(suborden > 0):
                self.jsonOutputs[ordenID]['answer']['steps'].append({})
            self.jsonOutputs[ordenID]['answer']['steps'][suborden]["worker_id"] = self.ID
            self.jsonOutputs[ordenID]['answer']['steps'][suborden]["step"] = suborden
            self.jsonOutputs[ordenID]['answer']['steps'][suborden]["state"] = "waiting to be cooked"
            self.jsonOutputs[ordenID]['answer']['steps'][suborden]['part_id'] = [
                ordenID, suborden][:]
            self.jsonOutputs[ordenID]['answer']['steps'][suborden]['time_stamp'] = getTime(
            )
        pass

    def is_order_rejectable(self, orden):
        for subOrden in orden['orden']:
            if((subOrden['type'] in self.allowedOrderTypes) \
                and (subOrden['meat'] in self.allowedMeatTypes) \
                and (subOrden['quantity'] > 0)):
                return False
        logging.info(f"order {orden['request_id']} has to be rejected")
        self.writeOutputSteps("rejectOrder",(orden['request_id'],0,0), None)
        return True
    
    def is_suborder_rejectable(self, orderID, suborden, suborderID):
        if((suborden['type'] in self.allowedOrderTypes) \
            and (suborden['meat'] in self.allowedMeatTypes) \
            and (suborden['quantity'] > 0)):
            return False
        else:
            logging.info(f"suborder {suborderID} had to be rejected")
            self.writeOutputSteps("rejectSuborder",(orderID,suborderID,0), None)
            return True
    
    def send_suborder_somewhere_else(self, suborder, order):
        # Revisar a donde lo mandaré
        # Mandar solamente la orden con la suborden buena
        # # veces que Omar olvido copiar por valor: >4 xdxd
        ordercopy = copy.deepcopy(order)
        for sub in ordercopy['orden']:
            if(sub["meat"] in self.meatTypes):
                ordercopy["orden"].remove(sub)
        indexToSend = self.cocinaDirectory[suborder["meat"]]
        self.sendQueues[indexToSend].put(ordercopy)
        pass
    
    def splitOrder(self, orden):
        pedido = orden
        numSuborden = 0
        rejectedSubs = []
        ### Primero reviso si toda la orden es rechazable
        if(self.is_order_rejectable(orden)):
            # Subir el contador de orden + 1 pero no registrarlo
            self.orderCounter += 1
            pass
        else: # Si la orden entera no era rechazable, procedamos
            # Seccionar en partes la orden (los indices de ['orden'])
            for subOrden in pedido['orden']:
                # Ok, la orden entera no es rechazable, pero que tal
                #  la suborden en sí
                if(self.is_suborder_rejectable(orden['request_id'], subOrden, numSuborden)):
                    # Si la suborden fue rechazable, movernos una sub hacia
                    # adelante en el contador
                    # El bloque de logica de abajo requiere saber cuales
                    #  fueron rechazadas, se marcarán como completas
                    #  silenciosamente
                    rejectedSubs.append(numSuborden)
                    numSuborden += 1
                    pass
                else:
                    # Ok, ya revisamos que la orden no es rechazable y que la 
                    #  suborden no es rechazable, pero que tal sí esta suborden
                    #  no es de mi carne?
                    if(subOrden["meat"] not in self.meatTypes):
                        #Tanto en output como en logica pondre el encargado
                        pedido["responsable_orden"] = self.ID
                        self.send_suborder_somewhere_else(subOrden, pedido)
                        numSuborden += 1
                        pass
                    else:
                        """[Explicación de la lista (TB DICT) que conforma al stacl]
                            stack = [
                                Costo UTIS del stack, 
                                Prioridad, 
                                TUPLA_ID - > (orden, suborden, stack), 
                                Tiempo de llegada desde epoch, 
                                Cantidad de tacos, 
                                Costo UTIS individual de cada taco, 
                                Tiempo para cocinar el stack, 
                                Tiempo individual para cocinar un taco, 
                                Tupla de ingredientes
                            ]
                        """
                        # Costo UTIS empieza en 1 por la carne, igual para tiempo de cocinar
                        costoUTIs = 1
                        tiempoParaCocinar = 1
                        subSplitIndex = 0
                        # Variables relacionadas con el uso de ingredientes
                        #  recordatorio: si una suborden usa x ingrediente, sus stacks tambien
                        #  y siempre se usan tortillas lol (to = *to*rtillas)
                        listaIngridients = ["", "", "", "", "to"]
                        if(subOrden['type'] == 'taco'):
                            # Hacer un calculo del costo
                            if('salsa' in subOrden['ingredients']):
                                costoUTIs += 2.66667
                                tiempoParaCocinar += 0.5
                                listaIngridients[0] = "sa"
                            if('guacamole' in subOrden['ingredients']):
                                costoUTIs += 3.5
                                tiempoParaCocinar += 0.5
                                listaIngridients[1] = "gu"
                            if('cilantro' in subOrden['ingredients']):
                                costoUTIs += 2
                                tiempoParaCocinar += 0.5
                                listaIngridients[2] = "ci"
                            if('cebolla' in subOrden['ingredients']):
                                costoUTIs += 2
                                tiempoParaCocinar += 0.5
                                listaIngridients[3] = "ce"
                            # costo es costo por taco * cantidadtacos
                            # Costo individual servirá para la división de sstacks
                            costoUTIsIndividual = costoUTIs
                            tiempoCocinarIndividual = tiempoParaCocinar
                            costoUTIs = costoUTIs * subOrden['quantity']
                            tiempoParaCocinar = tiempoParaCocinar * subOrden['quantity']

                            # Fin del calculo del costo
                            if(costoUTIs < self.constMagnitud):
                                # No dividir, solo 1 stack por esta suborden
                                prioridad = ((costoUTIs**-1)*10)
                                self.ordenesHeads.append(self.stackCounter)
                                subSplitIndex = 0
                                self.ordenes[str(self.stackCounter)] = {
                                    "costo utis": costoUTIs,
                                    "prioridad": prioridad,
                                    "tupleID": (self.orderCounter, numSuborden, subSplitIndex),
                                    "arrival time": time.time(),
                                    "quantity": subOrden['quantity'],
                                    "individual cost": costoUTIsIndividual,
                                    "time to cook": tiempoParaCocinar,
                                    "indiv. time to cook": tiempoCocinarIndividual,
                                    "ingridient list": listaIngridients
                                }
                                logging.info(
                                    f"Stack {self.stackCounter} has been put in {self.ID}'s head")
                                subSplitIndex += 1
                                self.stackCounter += 1
                            else:
                                # Dividir orden en partes (stacks)
                                # Primero ver cuantos stacks puedo hacer
                                # el tiempo para cocinar debe tomar en cuanta el numero de tacos
                                #  del stack en vez de la suborden si hubo particion
                                tacosPorStack = self.constMagnitud // costoUTIsIndividual
                                numStacks = subOrden['quantity'] // tacosPorStack
                                tiempoParaCocinar = tiempoCocinarIndividual * tacosPorStack
                                # calcular tacos sobrantes
                                tacosSobrantes = subOrden['quantity'] - (
                                    tacosPorStack * numStacks
                                )
                                residuoUTIS = costoUTIsIndividual * tacosSobrantes
                                if(numStacks == 1):
                                    # Pasar el taco sobrante al stack cola si solo
                                    #  hay 1 stack y su cola,
                                    tacosSobrantes = 1
                                    tacosPorStack -= 1
                                # Como habia hecho en el test2 inician
                                # primero vá la cola
                                # Si hubo residuo hay una "cola" para evitar problemas
                                # primero metamos a la cola la cabeza y que sus subse
                                # -cuenters grandes stacks sean vecinos
                                # Consultar con Omar para sus apuntes de estas lineas

                                # Si hubo residuo ponemos cola, si no entonces no
                                if(residuoUTIS > 0):
                                    prioridad = ((residuoUTIS**-1)*10)
                                    self.ordenesHeads.append(self.stackCounter)
                                    subSplitIndex = 0
                                    residuoTiempo = tiempoCocinarIndividual * tacosSobrantes
                                    self.ordenes[str(self.stackCounter)] = {
                                        "costo utis": residuoUTIS,
                                        "prioridad": prioridad,
                                        "tupleID": (self.orderCounter, numSuborden, subSplitIndex),
                                        "arrival time": time.time(),
                                        "quantity": tacosSobrantes,
                                        "individual cost": costoUTIsIndividual,
                                        "time to cook": residuoTiempo,
                                        "indiv. time to cook": tiempoCocinarIndividual,
                                        "ingridient list": listaIngridients
                                    }
                                    logging.info(
                                        f"Stack {self.stackCounter} has ben put in {self.ID}'s head")
                                    subSplitIndex += 1
                                    self.stackCounter += 1
                                else:
                                    # Si la orden esta partida perfectamente
                                    # en stacks iguales, le ponemos la cabeza aquí
                                    self.ordenesHeads.append(self.stackCounter)
                                for numStack in range(int(numStacks)):
                                    costoStack = tacosPorStack * costoUTIsIndividual
                                    prioridad = ((costoStack**-1)*10)
                                    self.ordenes[str(self.stackCounter)] = {
                                        "costo utis": costoUTIs,
                                        "prioridad": prioridad,
                                        "tupleID": (self.orderCounter, numSuborden, subSplitIndex),
                                        "arrival time": time.time(),
                                        "quantity": subOrden['quantity'],
                                        "individual cost": costoUTIsIndividual,
                                        "time to cook": tiempoParaCocinar,
                                        "indiv. time to cook": tiempoCocinarIndividual,
                                        "ingridient list": listaIngridients
                                    }
                                    logging.info(
                                        f"Stack {self.stackCounter} has ben put in {self.ID}'s head")
                                    subSplitIndex += 1
                                    self.stackCounter += 1
                                    pass
                                # Este bug ya no es necesario parchearlo así
                                # porque ahora estoy usando for y no while (creo..)
                                # self.stackCounter - = 1
                        numSuborden += 1
            # Antes de pasar a la siguiente orden, llenar el renglon de registro
            #  de cuales subordenes son de x orden
            renglonOrden = []
            for subordenesNumber in range(numSuborden):
                if(subordenesNumber not in rejectedSubs):
                    renglonOrden.append([subordenesNumber, 0])
                else:
                    renglonOrden.append([subordenesNumber, 1])
            self.ordenesSuborders[self.orderCounter] = renglonOrden
            self.orderCounter += 1
            pass

    def process_order(self, newOrder):
        logging.info(
            f"{self.name} está iniciando particion de orden {self.orderCounter}")
        self.Splitting = True
        #Primero se hace el output para poder ser rechazada
        self.startOutputtingOrder(newOrder)
        self.splitOrder(newOrder)  
        try:
            self.Rescheduling = True
            self.sortOrders()
            self.Rescheduling = False
            # Esto va aqui intencionalmente porque en esa corta ventana sin MUTEX
            # se podria agarrar un indice incorrecto porque no se alcanzaba a
            # ordear las ordenes
            self.Splitting = False
            logging.info(
                f"{self.name} ha finalizado la particion y organización de orden {self.orderCounter-1}")
        except Exception as e:
            logging.exception(
                f"Error en el sorting de ordenes - > {Exception}")
            pass
        pass
    
    def recieveOrders(self):
        while(True):
            #COMENTE ESTA PRIMERA LINEA PORQUE LAS ORDENES EN EL LOG HACE MUCHOOOO RUIDO
            logging.debug(self.ordenes)
            logging.info(self.ordenesSuborders)
            logging.info(f"{self.name}'s headsofOrders:{self.ordenesHeads}")
            logging.info(f"{self.name}'s taco counter: {self.tacoCounter}")
            logging.info(
                f"{self.name}'s remaining ingridients:{self.currentSalsa}|{self.currentGuacamole}|{self.currentCilantro}|{self.currentCebolla}|{self.currentTortillas}"
            )
            logging.info(
                f"Taquero {self.name} stats: OC:{self.orderCounterCompleted}|SOC:{self.subOrderCounter}|STC:{self.stackCounterCompleted}|TC:{self.tacoCounter}")
            # Placeholder de output json
            with open(f"outputs[{self.ID}].json", "w") as outputs:
                json.dump(self.jsonOutputs, outputs)
            # Placeholder end
            # Las ordenes se procesan a lo dos máximo cada delta
            if(not self.recieveQueue.empty()):
                self.ordersThatAreNotMine.append(self.orderCounter)
                self.process_order(self.recieveQueue.get_nowait())
            if(not self.queue.empty()):
                self.process_order(self.queue.get_nowait())
            
            # if debug_state is True:
            time.sleep(self.ordersPerSecondDelta)

    def sleep_handler(self):
        if(not self.isAnOwl):
            if(self.remainingRestingTime <= 0):
                # Si hubo muchos hangups, entonces hubo mucho descanso y no es
                #  necesario otro descanso, asi que solo se reinicia el contador
                logging.info(
                    f"Taquero {self.name} has already rested too much so he won't"
                )
                self.writeOutputSteps(
                    "noSleep", self.ordenes[self.shortestOrderIndex]["tupleID"], None)
                pass
            else:
                logging.info(
                    f"Taquero {self.name} must rest {self.remainingRestingTime} seconds"
                )
                self.writeOutputSteps(
                    "yesSleep", self.ordenes[self.shortestOrderIndex]["tupleID"], None)
                self.isResting = True
                time.sleep(self.remainingRestingTime)
                self.isResting = False
                logging.info(f"Taquero {self.name} has rested")
                self.writeOutputSteps(
                    "wakeUp", self.ordenes[self.shortestOrderIndex]["tupleID"], None)
                # Una vez que duerma reiniciar el contador de sleep
                pass
            # Reiniciar el contador de todos modos
            self.remainingRestingTime = self.maxRestingTime

    def checkOrderCompletion(self, orderToCheckIndex):
        # Funcion usada por endStack() para revisar si al acabar
        # un stack que acabó una suborden tambien acabó una orden
        allSubOrdersWereCompleted = True
        for suborden in self.ordenesSuborders[orderToCheckIndex]:
            # Indice 0 es suborden Index y indice 1 es su estado (0 vs 1)
            if(suborden[1] == 0):
                allSubOrdersWereCompleted = False
            pass
        if(allSubOrdersWereCompleted):
            # self.finisherOutput("order", (orderToCheckIndex, 0, 0))
            logging.info(
                f"{self.name}'s order {orderToCheckIndex} is complete")
            if(orderToCheckIndex not in self.ordersThatAreNotMine):
                # Solo sumar al contador si esta orden no era mía
                # el taquero dueño se encarga de reportar la finalización
                self.orderCounterCompleted += 1
            return True
        else:
            return False
        pass

    def endStack(self):
        # Variables para la logica del json output
        finishedASubOrder = False
        finishedAnOrder = False
        # Esta funcion es el ultimo bloque de logica
        # de la funcion de cocinar, cambia cabezas de ordenes y remueve de
        #  cosas por hacer los stacks hechos
        orderToCheckIndex = self.ordenes[self.shortestOrderIndex]["tupleID"][0]
        subOrderToEndIndex = self.ordenes[self.shortestOrderIndex]["tupleID"][1]
        if self.ordenes[self.shortestOrderIndex]["time to cook"] > 0:
            self.ordenes[str(self.shortestOrderIndex)
                         ]["time to cook"] -= self.cookUnitDelta
            # resta el costo del taco hecho
            if(self.ordenes[self.shortestOrderIndex]["time to cook"] == 0):
                # Remover de las ordenes cabeza
                # Poner la nueva cabeza si es necesario
                # y hacerle pop del diccionario de stacks/ordenes
                if(str(int(self.shortestOrderIndex)+1) in self.ordenes):
                    # primero revisar si hay un taco counter subsecuente
                    # Si se acabo el ultimo stack no hya porque revisar que exista
                    # un sucesor
                    if(self.ordenes[str(int(self.shortestOrderIndex)+1)]["tupleID"][0]
                       == self.ordenes[self.shortestOrderIndex]["tupleID"][0]):
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
                        # Si no quedan vecinos stacks, la suborden entonces
                        #  se acabó
                        self.subOrderCounter += 1
                        # Declarar en el registro de subordenes de ordenes
                        #   su completación (completición?)
                        self.ordenesSuborders[orderToCheckIndex
                                              ][subOrderToEndIndex][1] = 1
                        # self.finisherOutput("subOrder", (orderToCheckIndex, subOrderToEndIndex, 0))
                        logging.info(
                            f"{self.name}'s suborder {self.subOrderCounter} completed")
                        finishedASubOrder = True
                        # Revisar si se acabó la orden
                        finishedAnOrder = self.checkOrderCompletion(
                            orderToCheckIndex
                        )
                        # Revisar si se acabó la orden
                else:
                    # Si el ultimo elemento cocinado (en algun insante)
                    # era una cabeza que no pudo ser removida, la
                    # intentamos quitar
                    if(int(self.shortestOrderIndex) in self.ordenesHeads):
                        self.ordenesHeads.remove(
                            int(self.shortestOrderIndex))
                    # Cada removida de cabeza sin remplazarla == se acabó el stack
                    self.subOrderCounter += 1
                    # Declarar que suborden x de orden y se acabó
                    self.ordenesSuborders[orderToCheckIndex
                                          ][subOrderToEndIndex][1] = 1
                    # self.finisherOutput("subOrder", (orderToCheckIndex, subOrderToEndIndex, 0))
                    logging.info(
                        f"{self.name}'s suborder {self.subOrderCounter} completed")
                    finishedASubOrder = True
                    # Revisar si se acabó la orden
                    finishedAnOrder = self.checkOrderCompletion(
                        orderToCheckIndex)
                # Antes de hacer pop reportar su finalización en el json
                self.finisherOutput(
                    "stack", (
                        orderToCheckIndex,
                        subOrderToEndIndex,
                        self.ordenes[self.shortestOrderIndex]["tupleID"][2])
                )
                # Una vez acabado el proceso le hacemos pop
                # saca orden del taquero
                self.ordenes.pop(self.shortestOrderIndex, None)
                # Señalar al contador de stacks completos que se acabo uno más
                self.stackCounterCompleted += 1
                # Hacer los outputs de reporte luego de que se reporte el fin
                #  del stack, si es al mismo timestamp de todos modos
                #  pero así suena más lógico
                if(finishedASubOrder):
                    self.finisherOutput(
                        "subOrder", (orderToCheckIndex, subOrderToEndIndex, 0))
                if(finishedAnOrder):
                    self.finisherOutput("order", (orderToCheckIndex, 0, 0))
                logging.info(
                    f"{self.name}'s stack {self.shortestOrderIndex} completed")

                self.shortestOrderIndex = None

    def finisherOutput(self, type, tupID):
        # Primero reviso si esta orden es mía, si no no hago
        # esto y le mando devuelta al taquero normal
        orderID = tupID[0]
        subOrderID = tupID[1]
        stackID = tupID[2]
        nextStepID = len(self.jsonOutputs[orderID]["answer"]["steps"])
        step = {}
        step["worker_id"] = self.ID
        step["step"] = nextStepID
        step["state"] = None
        step["part_id"] = [orderID, subOrderID][:]
        step["time_stamp"] = getTime()
        if(type == "order"):
            step["state"] = f"Order {orderID} complete"
            self.jsonOutputs[orderID]["status"] = "complete"
        elif(type == "subOrder"):
            step["state"] = f"Suborder {subOrderID} complete"
        else:
            step["state"] = f"Stack#{stackID}({self.shortestOrderIndex}) complete"
        self.jsonOutputs[orderID]["answer"]["steps"].append(step)
        # Hacer una copia de esta orden en el output para mandarla al encargado
        # y borrarlo de mi parte, pero solo sí se acaba la orden
        if(orderID in self.ordersThatAreNotMine 
                and type == "order"):
            orderToReturn = copy.deepcopy(self.jsonOutputs[orderID])
            del self.jsonOutputs[orderID]
            # Ubicar a que queue se le debe regresar la orden
            # Todas las subs son iguales así que solo hay que revisar 1
            indexToReturnTo = orderToReturn["responsable_orden"]
            self.sendQueuesReturn[indexToReturnTo].put(orderToReturn)

    def writeOutputSteps(self, action, tupleID, extraArg):

        orderID = tupleID[0]
        subOrderID = tupleID[1]
        stackID = tupleID[2]
        if(self.shortestOrderIndex):
            numOfTacos = self.ordenes[self.shortestOrderIndex]["quantity"]
        else:
            numOfTacos = 0 #Ordenes rechazadas no tienen n tacos registrados
        step = {}
        step["worker_id"] = self.ID
        # Asignaciones de stack, suborden o orden
        if(action == "asigned"):
            # Scenario de cambio 1: ninguno jaja
            if(orderID == self.currentWorkingOrder and subOrderID == self.currentWorkingSuborder):
                # Pasar directamente a la sección de mero abajo de asigned
                pass
            # Scenario de cambio 2: cambio
            elif((orderID == self.currentWorkingOrder and subOrderID != self.currentWorkingSuborder)
                 or orderID != self.currentWorkingOrder):
                # Ahora crear otro paso que diga que esta suborden fue pausada
                # Saber que mensaje dar
                message = ""
                # Dos sub-escenarios, o cambia la orden o la suborden
                if(orderID == self.currentWorkingOrder):
                    message = f"Switching to suborder {subOrderID}"
                else:
                    message = f"Switching to order {orderID}"
                pauseStep = {}
                pauseStep["worker_id"] = self.ID
                pauseStep["step"] = len(
                    self.jsonOutputs[self.currentWorkingOrder]["answer"]["steps"])
                pauseStep["state"] = message
                pauseStep["part_id"] = [
                    self.currentWorkingOrder, self.currentWorkingSuborder]
                pauseStep["time_stamp"] = getTime()
                self.jsonOutputs[self.currentWorkingOrder]["answer"]["steps"].append(
                    pauseStep)
                # Y hagamos el nuevo paso de cooking en la activa
                pass
            nextStepID = len(self.jsonOutputs[orderID]["answer"]["steps"])
            step["step"] = nextStepID
            step["state"] = f"cooking stack #{stackID}({self.shortestOrderIndex}) of {numOfTacos} tacos"
            step["part_id"] = [orderID, subOrderID][:]
            step["time_stamp"] = getTime()
            self.jsonOutputs[orderID]["answer"]["steps"].append(step)
        elif(action == "fanON" or action == "fanOFF"):
            message = ""
            if(action == "fanON"):
                message = f"fan activation at {self.name}'s station"
            elif(action == "fanOFF"):
                message = f"fan deactivation at {self.name}'s station"
            # Se romperá esto cada eclipse lunar? vamoa a ver
            nextStepID = len(self.jsonOutputs[orderID]["answer"]["steps"])
            step["step"] = nextStepID
            step["state"] = message
            step["part_id"] = [orderID, subOrderID][:]
            step["time_stamp"] = getTime()
            self.jsonOutputs[orderID]["answer"]["steps"].append(step)
        elif(action == "wakeUp" or action == "noSleep" or action == "yesSleep"
             or action == "starving" or action == "unStarving" 
             or action == "rejectOrder" or action == "rejectSuborder"):
            message = ""
            if(action == "wakeUp"):
                message = f"Stopped resting"
            elif(action == "noSleep"):
                message = f"Decided that I will not rest because I was starving from resources before"
            elif(action == "yesSleep"):
                message = f"Resting"
            elif(action == "starving"):
                message = f"Starving, ran out out {extraArg}, currently resting"
            elif(action == "unStarving"):
                message = f"Chalan came back with {extraArg}, I can continue cooking"
            elif(action == "rejectOrder"):
                message = f"Rejected, we do not serve anything of that here"
                self.jsonOutputs[orderID]["status"] = "Rejected"
            elif(action == "rejectSuborder"):
                message = f"Suborder {subOrderID} rejected, invalid meat or type"
            nextStepID = len(self.jsonOutputs[orderID]["answer"]["steps"])
            step["step"] = nextStepID
            step["state"] = message
            step["part_id"] = [orderID, subOrderID][:]
            step["time_stamp"] = getTime()
            self.jsonOutputs[orderID]["answer"]["steps"].append(step)
            pass
        pass

    def requestIngridient(self, ingridient, quantity, priority):
        if(ingridient not in self.listOfRquestedIngridients):
            # Si no está el ingrediente en la lista de solicitados, se pide
            # Los taqueros individuales usan queueA, los paralelos queueB
            if(self.ID == 0 or self.ID == 3):
                queueChalan = self.chalanAsignado.queueA
            else:
                queueChalan = self.chalanAsignado.queueB
            # Chechar si es tortilla para darle el boost de prioridad
            if(ingridient == "to"):
                priority += self.tortillaRequestBoost
            # Cebolla y cilantro o nunca se rellenaban o lo hacian demasiado
            #  esto termina aqui y ahora de una vez por todas
            if(ingridient == "ce" or ingridient == "ci" or ingridient == "sa"):
                if((ingridient == "ce") and self.currentCebolla/self.maxCebolla
                        <= self.thresholdOfCilantroAndCebollaRequest):
                    self.listOfRquestedIngridients.append(ingridient)
                    queueChalan.put((ingridient, quantity, self.ID, priority))
                    pass
                elif((ingridient == "ci") and self.currentCilantro/self.maxCilantro
                     <= self.thresholdOfCilantroAndCebollaRequest):
                    self.listOfRquestedIngridients.append(ingridient)
                    queueChalan.put((ingridient, quantity, self.ID, priority))
                    pass
                elif((ingridient == "sa") and self.currentSalsa/self.maxSalsa
                     <= self.thresholdOfSalsaRequest):
                    self.listOfRquestedIngridients.append(ingridient)
                    queueChalan.put((ingridient, quantity, self.ID, priority))
                    pass
                elif((ingridient == "gu") and self.currentGuacamole/self.maxGuacamole
                     <= self.thresholdOfGuacamoleRequest):
                    self.listOfRquestedIngridients.append(ingridient)
                    queueChalan.put((ingridient, quantity, self.ID, priority))
                    pass
            else:
                queueChalan.put((ingridient, quantity, self.ID, priority))
                self.listOfRquestedIngridients.append(ingridient)
            # queueChalan.put_nowait((self, ingridient, quantity))
            # self.chalanAsignado.queueCabeza.append("lol")
            # Tambien se marca que se pidió, el chalan lo quita de tal listado
            # self.listOfRquestedIngridients.append(ingridient)
        pass

    def spendIngredients(self):
        # Lógica del consumo de ingredientes
        # hastag no se me vino esta idea de aquí https://youtu.be/LwKtRnlongU?t = 55
        if(not self.infiniteIngridients):
            if("to" in self.currentIngridientList):
                # Revisar si en la orden en la lista ingredientes se usa un ingrediente
                if(self.currentTortillas > 0):
                    # Si se tiene se gasta
                    self.currentTortillas -= 1
                    # Solicitar ingrediente
                    self.requestIngridient(
                        "to", self.maxTortillas-self.currentTortillas,
                        self.currentTortillas/self.maxTortillas)
                else:
                    # Si no se espera hasta que le llegue (temporal esta forma)
                    logging.info(f"Taquero {self.ID} waits for tortillas :(")
                    self.writeOutputSteps(
                        "starving", self.ordenes[self.shortestOrderIndex][2], "tortillas")
                    while(self.currentTortillas == 0):
                        time.sleep(0.1)
                        self.remainingRestingTime -= 0.1
                        if(self.currentTortillas > 0):
                            self.writeOutputSteps(
                                "unStarving", self.ordenes[self.shortestOrderIndex][2], "tortillas")
                    # Una vez llega sigue trabajando
                    self.currentTortillas -= 1
                # quitarlo de la lista al fin de todo modo
                self.currentIngridientList.remove("to")
            elif("sa" in self.currentIngridientList):
                if(self.currentSalsa > 0):
                    self.currentSalsa -= 1
                    self.requestIngridient("sa", self.maxSalsa-self.currentSalsa,
                                           self.currentSalsa/self.maxSalsa)
                else:
                    logging.info(f"Taquero {self.ID} waits for salsas :(")
                    self.writeOutputSteps(
                        "starving", self.ordenes[self.shortestOrderIndex][2], "salsas")
                    while(self.currentSalsa == 0):
                        time.sleep(0.1)
                        self.remainingRestingTime -= 0.1
                        if(self.currentSalsa > 0):
                            self.writeOutputSteps(
                                "unStarving", self.ordenes[self.shortestOrderIndex][2], "salsas")
                    self.currentSalsa -= 1
                self.currentIngridientList.remove("sa")
            elif("gu" in self.currentIngridientList):
                if(self.currentGuacamole > 0):
                    self.currentGuacamole -= 1
                    self.requestIngridient(
                        "gu", self.maxGuacamole-self.currentGuacamole,
                        self.currentGuacamole/self.maxGuacamole)
                else:
                    logging.info(f"Taquero {self.ID} waits for guacamoles")
                    self.writeOutputSteps(
                        "starving", self.ordenes[self.shortestOrderIndex][2], "guacamoles")
                    while(self.currentGuacamole == 0):
                        time.sleep(0.1)
                        self.remainingRestingTime -= 0.1
                        if(self.currentGuacamole > 0):
                            self.writeOutputSteps(
                                "unStarving", self.ordenes[self.shortestOrderIndex][2], "guacamoles")
                    self.currentGuacamole -= 1
                self.currentIngridientList.remove("gu")
            elif("ci" in self.currentIngridientList):
                if(self.currentCilantro > 0):
                    self.currentCilantro -= 1
                    self.requestIngridient(
                        "ci", self.maxCilantro-self.currentCilantro,
                        self.currentCilantro/self.maxCilantro)
                else:
                    logging.info(f"Taquero {self.ID} waits fot cilantro")
                    self.writeOutputSteps(
                        "starving", self.ordenes[self.shortestOrderIndex][2], "cilantros")
                    while(self.currentCilantro == 0):
                        time.sleep(0.1)
                        self.remainingRestingTime -= 0.1
                        if(self.currentCilantro > 0):
                            self.writeOutputSteps(
                                "unStarving", self.ordenes[self.shortestOrderIndex][2], "cilantros")
                    self.currentCilantro -= 1
                self.currentIngridientList.remove("ci")
            elif("ce" in self.currentIngridientList):
                if(self.currentCebolla > 0):
                    self.currentCebolla -= 1
                    self.requestIngridient(
                        "ce", self.maxCebolla-self.currentCebolla,
                        self.currentCebolla/self.maxCebolla)
                else:
                    logging.info(f"Taquero {self.ID} waits fot cebollas")
                    self.writeOutputSteps(
                        "starving", self.ordenes[self.shortestOrderIndex][2], "cebollas")
                    while(self.currentCebolla == 0):
                        time.sleep(0.1)
                        self.remainingRestingTime -= 0.1
                        if(self.currentCebolla > 0):
                            self.writeOutputSteps(
                                "unStarving", self.ordenes[self.shortestOrderIndex][2], "cebollas")
                    self.currentCebolla -= 1
                self.currentIngridientList.remove("ce")

    def checkIngridients(self):
        if(not self.infiniteIngridients):
            # Esto intenta aliviar el error de diseño en que no se piden ingredientes
            #  faltantes porque no se usan (y solo se hacia la llamada de requestIngridients() en el uso)
            if((self.currentSalsa != self.maxSalsa) and ("sa" not in self.listOfRquestedIngridients)):
                self.requestIngridient("sa", self.maxSalsa - self.currentSalsa,
                                       self.maxSalsa/(self.currentSalsa))
            if((self.currentGuacamole != self.maxGuacamole) and ("gu" not in self.listOfRquestedIngridients)):
                self.requestIngridient("gu", self.maxGuacamole - self.currentGuacamole,
                                       self.maxGuacamole/(self.currentGuacamole))
            if((self.currentCebolla != self.maxCebolla) and ("ce" not in self.listOfRquestedIngridients)):
                self.requestIngridient("ce", self.maxCebolla - self.currentCebolla,
                                       self.maxCebolla/(self.currentCebolla))
            if((self.currentCilantro != self.maxCilantro) and ("ci" not in self.listOfRquestedIngridients)):
                self.requestIngridient("ci", self.maxCilantro - self.currentCilantro,
                                       self.maxCilantro/(self.currentCilantro))
            if((self.currentCilantro != self.maxTortillas) and ("to" not in self.listOfRquestedIngridients)):
                self.requestIngridient("to", self.maxTortillas - self.currentTortillas,
                                       self.maxTortillas/(self.currentTortillas))

    def pickShortestOrderIndex(self):
        # Esperar a que no se este haciendo sort o split para conseguir
        #  un indice con el que trabajar
        if((not self.Splitting) and (not self.Rescheduling)):
            # Sí actualmente no trabaja en un stack, darle el indice
            # TODO referirlo como biggestPriorityIndex
            # Sacada respuesta de
            # https://stackoverflow.com/a/64152259 por Sloper C. (2020)
            # el key 0 es de la lista hecha diccionario con la prioridad
            # $  mas grande
            logging.info(f"Taquero {self.name} will sort to pick")
            self.sortOrders()
            logging.info(f"Taquero {self.name} has sorted and will pick")
            self.shortestOrderIndex = str(list(self.ordenes.keys())[0])
            # Tambien que agarre la lista de ingredientes que se usa x cada taco
            # Explicitamente debe hacerce por valor porque la original debe restaurarse
            #  N tacos por cada stack [:] hace eso
            self.currentIngridientList = self.ordenes[self.shortestOrderIndex]["ingridient list"].copy()
            logging.info(
                f"{self.name} current working stack is now: {self.shortestOrderIndex}")
            # Varia por stack, cada x deltas se hace un taco y debemos contarlos
            self.deltasPerTaco = self.ordenes[self.shortestOrderIndex]["indiv. time to cook"] / \
                self.cookUnitDelta
            # acabaste de escojer taquero? ...chido, ahora escribelo en el JSOP
            orderID = self.ordenes[self.shortestOrderIndex]["tupleID"][0]
            suborderID = self.ordenes[self.shortestOrderIndex]["tupleID"][1]
            stackID = self.ordenes[self.shortestOrderIndex]["tupleID"][2]
            # Sección de codigo exlcuisva del json output
            if(self.currentWorkingOrder == None):
                self.currentWorkingOrder = self.ordenes[self.shortestOrderIndex]["tupleID"][0]
                self.currentWorkingSuborder = self.ordenes[self.shortestOrderIndex]["tupleID"][1]
                self.currentWorkingStack = self.shortestOrderIndex
            self.writeOutputSteps(
                "asigned", (orderID, suborderID, stackID), None
            )
            self.currentWorkingOrder = self.ordenes[self.shortestOrderIndex]["tupleID"][0]
            self.currentWorkingSuborder = self.ordenes[self.shortestOrderIndex]["tupleID"][1]
            self.currentWorkingStack = self.shortestOrderIndex
            ##
        else:
            if(self.shortestOrderIndex == None):
                logging.info(
                    f"Taquero {self.name}is splitting or scheduling, cannot pick  a new index")
        pass

    def cook(self):
        while(True):
            if(bool(self.ordenes)):
                # Escojer indice para trabajar si no se tiene uno
                if(self.shortestOrderIndex == None):
                    self.pickShortestOrderIndex()
                else:
                    # Si no que siga trabajando con ese stack incluso si
                    # llega a haber un sort nuevo con orden más chica
                    pass
                # Cocinamos si no se esta recalendarizando por parte del taquero (el taxer no
                #  activa el MUTEX intencionalmente) y si hay indice disponible
                # Tampoco si se esta haciendo algun split el taquero porque ni que tuviera
                #  4 brazos y dos cerebros lol
                if(not self.Rescheduling
                        and not self.Splitting
                        and self.shortestOrderIndex != None):
                    # Esta variable la vamos a usar?....
                    self.Cooking = True
                    # La delta ahora se hace primero para evitar reporte
                    # prematura de completicion de stack
                    # if debug_state is True:
                    time.sleep(self.cookUnitDelta)
                    # Gastar ingredientes
                    self.spendIngredients()
                    # Checar si faltan ingredientes incluso si no se usaron
                    self.checkIngridients()
                    # Logica del taco counter
                    self.deltasPerTaco -= 1
                    if(self.deltasPerTaco == 0):
                        self.tacoCounter += 1
                        # Reiniciar el contador para que calcule las deltas de otro taco
                        #  del mismo tamano dentro del stack
                        self.deltasPerTaco = self.ordenes[self.shortestOrderIndex]["indiv. time to cook"] / \
                            self.cookUnitDelta
                        # Tambien reiniciar el listado de ingredientes por cada taco
                        #  porque cada taco puede usar 1 ingrediente de cada tipo, no un stack
                        # Aquí tambien debe copiarse por valor y no referencia
                        self.currentIngridientList = self.ordenes[self.shortestOrderIndex]["ingridient list"].copy()
                        # Revisar si tiene que descansar una vez que acaba el
                        #   taco y sabe que se hará en el siguiente, o sea
                        #   que al acabar cad a x tacos verá cuanto debe sleep
                        if(self.tacoCounter > 0 and
                                self.tacoCounter % self.tacosRestingThreshold == 0):
                            self.sleep_handler()
                    # Lógica de restar tiempo, quitar cabezas y hacer pop
                    # Ver si le queda tiempo por cocinar al stack, si no quitar
                    self.endStack()
            else:
                self.Cooking = False

    def starvingTaxer(self):
        while(True):
            # Link para explicación gráfica de los impuestos
            # https://www.desmos.com/calculator/ksquctjgyz
            # Siempre estar dando impuestos a las cabezas cada segundo y haciendo
            # sort ¿tardá mucho? ya veremos jesjes
            for headIndex in self.ordenesHeads:
                try:
                    UTIs = self.ordenes[str(headIndex)]["costo utis"]
                    base = (UTIs ** -1) * 10
                    tax = (
                        UTIs
                        * self.constStarving
                        * (time.time() - self.ordenes[str(headIndex)]["arrival time"])
                    )
                    self.ordenes[str(headIndex)]["prioridad"] = (base + tax)
                except Exception as e:
                    logging.error(
                        f"Concurrency error at {self.name}'s  taxer, tried to tax a head in transition to death"
                    )

            if debug_state is True:
                time.sleep(1.0)

    def sortOrders(self):
        logging.info("Sorting start")
        # Primero sortear por desempate FCFS (se hace esto primero desempate y luego el bueno)
        lol = dict(self.ordenes.items())
        sortedOrders = sorted(self.ordenes.items(),
                              key=lambda item: item[1]["arrival time"])
        # Luego sortear por pioridad donde mas es mas importante
        # Basado en esta respuesta de stack overflow
        # https://stackoverflow.com/questions/18414995/how-can-i-sort-tuples-by-reverse-yet-breaking-ties-non-reverse-python/18415853#18415853
        sortedOrders = sorted(self.ordenes.items(),
                              key=lambda item: item[1]["prioridad"], reverse=True)
        self.ordenes = dict(sortedOrders)
        logging.info("Sorting end")
        pass

    def fanChecker(self):
        # Thread que se encarga de revisar el taco counter y encender
        # el ventilador cuando es necesario
        deltaA = self.tacoCounter
        while(True):
            # La operacion sera division residuo
            deltaB = self.tacoCounter
            # si la resta entre B - A es > que tl threshold, encender
            # ventilador
            if((deltaB - deltaA) >= self.fanThreshold):
                self.isFanActive = True
                logging.info(
                    f"{self.name}'s fan has been activated at a TC of {self.tacoCounter}"
                )
                try:
                    self.writeOutputSteps(
                        "fanON", self.ordenes[self.shortestOrderIndex]["tupleID"], None)
                except Exception as e:
                    logging.error("My fan was turned on while not cooking")
                time.sleep(self.useTimeOfFan)
                logging.info(
                    f"{self.name}'s fan is off"
                )
                try:
                    self.writeOutputSteps(
                        "fanOFF", self.ordenes[self.shortestOrderIndex]["tupleID"], None)
                except Exception as e:
                    logging.error("My fan was turned off while not cooking")
                deltaA = self.tacoCounter
            # Estar checando cada 0.25  segs, que es un intervalo más
            #  pequeño que le delta de cocina, por lo tanto no *deberia* fallar
            time.sleep(0.20)


class ChalanTaquero(threading.Thread):
    def __init__(self, _name):
        # SuperConsteructor
        super(ChalanTaquero, self).__init__(target=self.main, name=_name)
        # Cada chalan tiene dos taqueros asignados, por lo tanto debe haber dos queues de solicitudes
        #    si fuesemos a verlo de forma IRL, digamos que el taquero le escribio en un pizarron
        #    al chalan la solicitud y este debe meterlo en su cabeza su tarea

        self.queueA = multiprocessing.Queue()
        self.queueB = multiprocessing.Queue()
        # Aquí estan las solicitudes ya en la cabeza del chalan
        self.priorityQueueCabeza = []
        # Apuntador a los cocineros asignados (A es el solo, B es de los paralelos)
        #  lo asigna la cocina
        self.cocinerosAsignados = [None, None]
        pass

    def sortRequests(self):
        """
            [Tabla de prioridades]
            1)Tortillas (se gastan siempre y rápido :c )
            2)Guacamole
            3)Salsa
            4)Cebolla y cilantro 
        """
        self.priorityQueueCabeza = sorted(
            self.priorityQueueCabeza,
            key=lambda x: x[3],
            reverse=True
        )
        pass

    def gotoStoreAndRefill(self, orderTypeToRefill, taqueroIDToRefill, quantityToRefill, timeToRefill):
        # Imprimir la lista de solicitudes si no está vacia
        logging.info(self.priorityQueueCabeza)
        # Hacer el relleno yendo a la tienda
        logging.info(
            f"Chalan will go to the store for {orderTypeToRefill}")
        time.sleep(timeToRefill)
        if(taqueroIDToRefill == 3):
            taqueroIDToRefill = 0 # 0 y 3 son 0, 1 y 2 son 1
        if(orderTypeToRefill == "to"):
            self.cocinerosAsignados[taqueroIDToRefill].currentTortillas += quantityToRefill
            # Decirle al taquero que ya le dio los ingredientes solicitados
            self.cocinerosAsignados[taqueroIDToRefill].listOfRquestedIngridients.remove(
                "to")
            logging.info(
                f"Chalan returned and has given {quantityToRefill} tortillas to taquero {taqueroIDToRefill}")
        elif(orderTypeToRefill == "sa"):
            self.cocinerosAsignados[taqueroIDToRefill].currentSalsa += quantityToRefill
            self.cocinerosAsignados[taqueroIDToRefill].listOfRquestedIngridients.remove(
                "sa")
            logging.info(
                f"Chalan returned and has given {quantityToRefill} salsas to taquero {taqueroIDToRefill}")
        elif(orderTypeToRefill == "gu"):
            self.cocinerosAsignados[taqueroIDToRefill].currentGuacamole += quantityToRefill
            self.cocinerosAsignados[taqueroIDToRefill].listOfRquestedIngridients.remove(
                "gu")
            logging.info(
                f"Chalan returned and has given {quantityToRefill} guacamoles to taquero {taqueroIDToRefill}")
        elif(orderTypeToRefill == "ci"):
            self.cocinerosAsignados[taqueroIDToRefill].currentCilantro += quantityToRefill
            self.cocinerosAsignados[taqueroIDToRefill].listOfRquestedIngridients.remove(
                "ci")
            logging.info(
                f"Chalan returned and has given {quantityToRefill} cilantros to taquero {taqueroIDToRefill}")
        elif(orderTypeToRefill == "ce"):
            self.cocinerosAsignados[taqueroIDToRefill].currentCebolla += quantityToRefill
            self.cocinerosAsignados[taqueroIDToRefill].listOfRquestedIngridients.remove(
                "ce")
            logging.info(
                f"Chalan returned and has given {quantityToRefill} cebollas to taquero {taqueroIDToRefill}")
        # Remover de la cabeza
        self.priorityQueueCabeza.pop(0)

    def main(self):
        print(f"Chalan {self.name} en linea")
        # Estar escuchando a los taqueros asignados a que le digan algo
        while(True):
            # Variables para el relleno de ingredientes
            timeToRefill = 0
            quantityToRefill = 0
            taqueroIDToRefill = 0
            orderTypeToRefill = ""
            # Escucha ambas solicitudes y luego decide irse o no a la tienda y rellenar
            if(self.queueA.empty()):
                pass
            else:
                # Si hubo una solicitud de rellenar que lo lea del pizarron, que se lo meta en su cabeza
                while(not self.queueA.empty()):
                    self.priorityQueueCabeza.append(self.queueA.get_nowait())
            pass
            if(self.queueB.empty()):
                pass
            else:
                while(not self.queueB.empty()):
                    self.priorityQueueCabeza.append(self.queueB.get_nowait())
            pass
            # Decidir si tiene que rellenar algo en base a la solicitud más reciente
            if(len(self.priorityQueueCabeza) > 0):
                self.sortRequests()
                quantityToRefill = self.priorityQueueCabeza[0][1]
                taqueroIDToRefill = self.priorityQueueCabeza[0][2]
                if(self.priorityQueueCabeza[0][0] == "to"):
                    timeToRefill = 5
                    orderTypeToRefill = "to"
                elif(self.priorityQueueCabeza[0][0] == "sa"):
                    timeToRefill = 15
                    orderTypeToRefill = "sa"
                elif(self.priorityQueueCabeza[0][0] == "gu"):
                    timeToRefill = 20
                    orderTypeToRefill = "gu"
                elif(self.priorityQueueCabeza[0][0] == "ci"):
                    timeToRefill = 10
                    orderTypeToRefill = "ci"
                elif(self.priorityQueueCabeza[0][0] == "ce"):
                    timeToRefill = 10
                    orderTypeToRefill = "ce"
                pass
            else:
                # Si no hay ordenes entonces que siga estando al tanto
                pass

            if(len(self.priorityQueueCabeza) > 0):
                # Si hay tareas, ir a la tienda y rellenar
                self.gotoStoreAndRefill(
                    orderTypeToRefill, taqueroIDToRefill, quantityToRefill, timeToRefill
                )

            # Volver a revisar los pizarrones, necesario ese sleep?
            time.sleep(0.25)
        pass


class CocinaTaqueros(multiprocessing.Process):
    def __init__(self, _name):
        # SuperConsteructor
        super(CocinaTaqueros, self).__init__(target=self.main, name=_name)
        self.personal = []
        self.commsDelta = 0.5  # segundos hace un refresh de envio de datos

        pass

    def main(self):
        print("Cocina encendida")
        print(
            "Puente hacia el disco casi abierto lol #$%^& Windows y su falta de fork()")

    def ingreso_personal(self, cocina):
        #         # Queues de mandar pedidos o recibir pedidos no correspondientes
        # self.sendQueues = [None,None,None,None]
        # self.recieveQueues = None
        # # Queues de mandar o recibir pedidos no correspondientes hechos
        # self.sendQueuesReturn = [None,None,None,None]
        # self.recieveQueuesReturn = None
        """
        [IDs de taqueros]
            0 - > Adobaba
            1 - > Asada y Suadero (1)
            2 - > Asada y Suadero (2)
            3 - > Tripa y cabeza 
            4 - > El de las quesadillas
        """
        # Aviso: la cocina no puede hacer esto en primer persona
        # (o sea con self), si se hace no pasa nada o pasan comportamientos
        #  no deseados para Omar
        # El queue send de uno es el receptor de otro y viceversa
        for i in range(4):
            cocina.personal.append(None)
                    
        cocina.personal[0] = PersonalTaqueria("Omar")
        cocina.personal[0].chalanAsignado = ChalanTaquero("Julio")
        cocina.personal[0].chalanAsignado.cocinerosAsignados[0] = cocina.personal[0]
        cocina.personal[0].ID = 0
        cocina.personal[0].meatTypes = ["adobada"]
        # Marcelino pospuesto hasta acabar la lógica individual
        cocina.personal[3] = PersonalTaqueria("Jerry")
        cocina.personal[3].chalanAsignado = ChalanTaquero("Adan")
        cocina.personal[3].chalanAsignado.cocinerosAsignados[0] = cocina.personal[3]
        cocina.personal[3].ID = 3
        cocina.personal[3].meatTypes = ["tripa","cabeza"]
        
        for i in range(4):
            try:
                for j in range(4):
                    cocina.personal[i].sendQueues.append(None)
                    cocina.personal[i].sendQueuesReturn.append(None)
            except:
                print(f"Proximamente en la taqueria, el taquero {i}")

        # Asignar buses de envio y recibo de ordenes
        cocina.personal[0].recieveQueue = Queue()
        cocina.personal[3].recieveQueue = Queue()
        cocina.personal[0].sendQueues[3] =  cocina.personal[3].recieveQueue
        cocina.personal[3].sendQueues[0] =  cocina.personal[0].recieveQueue
        # Asignar buses de envio y recibo de retornes de (sub)ordenes completas
        cocina.personal[0].recieveQueueReturn = Queue()
        cocina.personal[3].recieveQueueReturn = Queue()
        cocina.personal[0].sendQueuesReturn[3] =  cocina.personal[3].recieveQueueReturn
        cocina.personal[3].sendQueuesReturn[0] =  cocina.personal[0].recieveQueueReturn
        
        #Arrancar los threads        
        cocina.personal[0].start()
        cocina.personal[0].chalanAsignado.start()
        
        cocina.personal[3].start()
        cocina.personal[3].chalanAsignado.start()
        
class CocinaQuesadillero():
    pass

def open_taqueria():
    # Solo poner estas ordenes mientras hacemos pruebas
    ordersToTest = 1
    # si se desean ver ordenes en cabeza, cambiar nivel a debug
    logging.basicConfig(level=logging.DEBUG, filename="logfile.log", filemode="w",
                        format="%(asctime)s - [%(levelname)s] - [%(threadName)s] - %(name)s - (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s")
    Cocina = CocinaTaqueros("Taqueros")
    Cocina.start()
    Cocina.ingreso_personal(Cocina)
   
    
    while(True):
        with open("someOneElses.json") as OrdenesJSON:
            ListadoOrdenes = json.load(OrdenesJSON)
            for i in range(ordersToTest):
                orden = ListadoOrdenes[i]
                Cocina.personal[0].queue.put(orden)
        time.sleep(999999)
