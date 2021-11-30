import multiprocessing
from queue import Empty, PriorityQueue
import queue
import emoji
import threading
import logging
import datetime
import string
import time
import json
import copy
from time import sleep
import sys
abcdario = list(string.ascii_uppercase)
debug_state = True

def getTime():
    LocalTime = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
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
        self.FanThread = threading.Thread(
            target=self.fanChecker,
            args=()
        )
        self.saving_memory = threading.Thread(
            target=self.staff_to_json, args=())

        self.emojis = ''
        # Variables de pertnenencia
        self.ID = None
        self.meatType = None
        self.allowedMeatTypes = ["suadero","adobada","asada","cabeza","tripa"]
        # Variables MUTEX
        self.Splitting = False
        self.Rescheduling = False
        self.Cooking = False
        # Esctructuras de datos y cosas del output
        self.jsonOutputTemplate = None # Se asigna en main
        self.hasCookedSomething = False
        self.jsonOutputs = {}  # Cuadrerno con los jsons de salida
        self.ordenes = {}  # dict in mind per worker
        self.ordenesHeads = []  # lista con las cabezas de subordenenes
        self.ordenesSuborders = {}  # Dict con listas de listas sobordenes
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
            sleep(5)  # HERE WE SET THE SAVING TO DISK INTERVAL e.g., 3 seconds <-
            print(f"-> saving {self.name} at {getTime()} ...")
            self.objects_to_json()

    def objects_to_json(self):
        path = 'logs/staff/taqueros/'+self.name+'.json'
        with open(path, mode='w', encoding='utf-8') as file:
            serialized = {'name': self.name, 'ID': self.ID, 'ordenes': self.ordenes, 'stackcounter': self.stackCounter,
                          'isFanActive': self.isFanActive, 'chalan': self.chalanAsignado.name, 'cooking': self.Cooking}
            json.dump(serialized, file)
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
        #Funcion que crea un indice en los outputs de salidas
        #  lo hace en base al templete lul     
        ordenID = orden['request_id']
        logging.info(f"Outputting input of {ordenID}")
        # condenado seas python y tu inabilidad de copiar cosas por valor al 100%
        copia = copy.deepcopy(self.jsonOutputTemplate["orderIDGoesHere"])
        self.jsonOutputs[ordenID] = copia
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
            self.jsonOutputs[ordenID]['answer']['steps'][suborden]['part_id'] = [ordenID,suborden][:]
            self.jsonOutputs[ordenID]['answer']['steps'][suborden]['time_stamp'] = getTime()
        pass
    
    def SplitOrder(self, orden):
        pedido = orden
        numSuborden = 0
        # Seccionar en partes la orden (los indices de ['orden'])
        for subOrden in pedido['orden']:
            """[Explicación de la lista que conforma al stacl]
                stack = [
                    Costo UTIS del stack,
                    Prioridad,
                    TUPLA_ID -> (orden, suborden, stack),
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
                    self.ordenes[str(self.stackCounter)] = [
                        costoUTIs,
                        prioridad,
                        (self.orderCounter, numSuborden, subSplitIndex),
                        time.time(),
                        subOrden['quantity'],
                        costoUTIsIndividual,
                        tiempoParaCocinar,
                        tiempoCocinarIndividual,
                        listaIngridients
                    ]
                    logging.info(
                        f"Stack {self.stackCounter} has been put ahead")
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
                        self.ordenes[str(self.stackCounter)] = [
                            residuoUTIS,
                            prioridad,
                            (self.orderCounter, numSuborden, subSplitIndex),
                            time.time(),
                            tacosSobrantes,
                            costoUTIsIndividual,
                            residuoTiempo,
                            tiempoCocinarIndividual,
                            listaIngridients
                        ]
                        logging.info(
                            f"Stack {self.stackCounter} has ben put in head")
                        subSplitIndex += 1
                        self.stackCounter += 1
                    else:
                        # Si la orden esta partida perfectamente
                        # en stacks iguales, le ponemos la cabeza aquí
                        self.ordenesHeads.append(self.stackCounter)
                    for numStack in range(int(numStacks)):
                        costoStack = tacosPorStack * costoUTIsIndividual
                        prioridad = ((costoStack**-1)*10)
                        self.ordenes[str(self.stackCounter)] = [
                            costoStack,
                            prioridad,
                            (self.orderCounter, numSuborden, subSplitIndex),
                            time.time(),
                            tacosPorStack,
                            costoUTIsIndividual,
                            tiempoParaCocinar,
                            tiempoCocinarIndividual,
                            listaIngridients
                        ]
                        logging.info(
                            f"Stack {self.stackCounter} has ben put in head")
                        subSplitIndex += 1
                        self.stackCounter += 1
                        pass
                    # Este bug ya no es necesario parchearlo así
                    # porque ahora estoy usando for y no while (creo..)
                    #self.stackCounter -=1
                    pass
                pass
            pass
            numSuborden += 1
        # Antes de pasar a la siguiente orden, llenar el renglon de registro
        #  de cuales subordenes son de x orden
        renglonOrden = []
        for subordenesNumber in range(numSuborden):
            renglonOrden.append([subordenesNumber, 0])
        self.ordenesSuborders[self.orderCounter] = renglonOrden
        self.orderCounter += 1
        pass

    def recieveClientOrders(self):
        while(True):
            logging.info(self.ordenes)
            logging.info(self.ordenesSuborders)
            logging.info(f'HeadsofOrders:{self.ordenesHeads}')
            logging.info(f"Taco counter: {self.tacoCounter}")
            logging.info(
                f"Remaining ingridients:{self.currentSalsa}|{self.currentGuacamole}|{self.currentCilantro}|{self.currentCebolla}|{self.currentTortillas}"
            )
            logging.info(
                f"Taquero {self.name} stats: OC:{self.orderCounterCompleted}|SOC:{self.subOrderCounter}|STC:{self.stackCounterCompleted}|TC:{self.tacoCounter}")
            ###Placeholder de output json
            with open("outputs.json", "w") as outputs:
                json.dump(self.jsonOutputs,outputs)
            ####Placeholder end
            if(self.queue.empty()):
                pass
            else:
                newOrder = self.queue.get_nowait()
                logging.info("Iniciando particion de orden x")
                self.Splitting = True
                self.SplitOrder(newOrder)
                self.startOutputtingOrder(newOrder)
                # self.Splitting = False
                # logging.info("Finalizada la particion y organización de orden x")
                try:
                    self.Rescheduling = True
                    self.sortOrders()
                    self.Rescheduling = False
                    # Esto va aqui intencionalmente porque en esa corta ventana sin MUTEX
                    # se podria agarrar un indice incorrecto porque no se alcanzaba a
                    # ordear las ordenes
                    self.Splitting = False
                    logging.info(
                        "Finalizada la particion y organización de orden x")
                except Exception as e:
                    logging.exception(f"Error -> {Exception}")
                    pass
            # if debug_state is True:
            time.sleep(self.ordersPerSecondDelta)
    
    def sleepHandler(self):
        if(not self.isAnOwl):
            if(self.remainingRestingTime <= 0):
                # Si hubo muchos hangups, entonces hubo mucho descanso y no es
                #  necesario otro descanso, asi que solo se reinicia el contador
                logging.info(
                    f"Taquero {self.name} has already rested too much so he won't"
                )
                pass
            else:
                logging.info(
                    f"Taquero {self.name} must rest {self.remainingRestingTime} seconds")
                self.isResting = True
                time.sleep(self.remainingRestingTime)
                self.isResting = False
                logging.info(f"Taquero {self.name} has rested")
                # Una vez que duerma reiniciar el contador de sleep
                pass
            # Reiniciar el contador de todos modos
            self.remainingRestingTime = self.maxRestingTime
    
    def checkOrderCompletion(self, orderToCheckIndex):
        #Funcion usada por endStack() para revisar si al acabar
        # un stack que acabó una suborden tambien acabó una orden
        allSubOrdersWereCompleted = True
        for suborden in self.ordenesSuborders[orderToCheckIndex]:
            #Indice 0 es suborden Index y indice 1 es su estado (0 vs 1)
            if(suborden[1] == 0):
                allSubOrdersWereCompleted = False
            pass
        if(allSubOrdersWereCompleted):
            #self.finisherOutput("order",(orderToCheckIndex,0,0))
            logging.info(f"Order {orderToCheckIndex} is complete")
            self.orderCounterCompleted += 1
            return True
        else:
            return False
        pass
    
    def endStack(self):
        ## Variables para la logica del json output
        finishedASubOrder = False
        finishedAnOrder = False
        # Esta funcion es el ultimo bloque de logica
        # de la funcion de cocinar, cambia cabezas de ordenes y remueve de
        #  cosas por hacer los stacks hechos
        orderToCheckIndex = self.ordenes[self.shortestOrderIndex][2][0]
        subOrderToEndIndex = self.ordenes[self.shortestOrderIndex][2][1]
        if self.ordenes[self.shortestOrderIndex][6] > 0:
            self.ordenes[str(self.shortestOrderIndex)
                         ][6] -= self.cookUnitDelta
            # resta el costo del taco hecho
            if(self.ordenes[self.shortestOrderIndex][6] == 0):
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
                        # Si no quedan vecinos stacks, la suborden entonces
                        #  se acabó
                        self.subOrderCounter += 1
                        # Declarar en el registro de subordenes de ordenes
                        #   su completación (completición?)
                        self.ordenesSuborders[orderToCheckIndex
                        ][subOrderToEndIndex][1] = 1
                        #self.finisherOutput("subOrder",(orderToCheckIndex,subOrderToEndIndex,0))
                        logging.info(f"Suborder {self.subOrderCounter} completed")
                        finishedASubOrder = True
                        self.checkOrderCompletion(orderToCheckIndex) 
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
                    #self.finisherOutput("subOrder",(orderToCheckIndex,subOrderToEndIndex,0))
                    logging.info(f"Suborder {self.subOrderCounter} completed")
                    finishedASubOrder = True
                    # Revisar si se acabó la orden
                    finishedAnOrder = self.checkOrderCompletion(orderToCheckIndex) 
                # Una vez acabado el proceso le hacemos pop
                # saca orden del taquero
                self.ordenes.pop(self.shortestOrderIndex, None)
                # Señalar al contador de stacks completos que se acabo uno más
                self.stackCounterCompleted += 1
                self.finisherOutput(
                    "stack",(
                        orderToCheckIndex,
                        subOrderToEndIndex,
                        int(self.shortestOrderIndex))
                )
                # Hacer los outputs de reporte luego de que se reporte el fin
                #  del stack, si es al mismo timestamp de todos modos
                #  pero así suena más lógico
                if(finishedASubOrder):
                    self.finisherOutput("subOrder",(orderToCheckIndex,subOrderToEndIndex,0))
                if(finishedAnOrder):
                    self.finisherOutput("order",(orderToCheckIndex,0,0))
                logging.info(
                    f"Stack {self.shortestOrderIndex} completed")

                self.shortestOrderIndex = None

    def finisherOutput(self,type,tupID):
        orderID = tupID[0]
        subOrderID = tupID[1]
        stackID = tupID[2]
        nextStepID = len(self.jsonOutputs[orderID]["answer"]["steps"])
        step = {}
        step["worker_id"] = self.ID
        step["step"] = nextStepID
        step["state"] = None
        step["part_id"] = [orderID,subOrderID][:]
        step["time_stamp"] = getTime()
        if(type=="order"):
            step["state"] = f"Order {orderID} complete"
            pass
        elif(type=="subOrder"):
            step["state"] = f"Suborder {subOrderID} complete"
            pass
        else:
            step["state"] = f"Stack {stackID} complete"
            pass 
        self.jsonOutputs[orderID]["answer"]["steps"].append(step) 
        pass
    
    def writeOutputSteps(self, action, tupleID):
        orderID = tupleID[0]
        subOrderID = tupleID[1]
        stackID = tupleID[2]
        numOfTacos = self.ordenes[self.shortestOrderIndex][4]
        # Scenario de cambio 1: ninguno jaja 
        if(orderID == self.currentWorkingOrder and subOrderID == self.currentWorkingSuborder):
            nextStepID = len(self.jsonOutputs[orderID]["answer"]["steps"])
            step = {}
            if(action == "asigned"):
                step["worker_id"] = self.ID
                step["step"] = nextStepID
                step["state"] = f"cooking stack #{self.shortestOrderIndex} of {numOfTacos} tacos"
                step["part_id"] = [orderID,subOrderID][:]
                step["time_stamp"] = getTime()
                self.jsonOutputs[orderID]["answer"]["steps"].append(step)            
        # Scenario de cambio 2: misma orden otra suborden
        elif((orderID == self.currentWorkingOrder and subOrderID != self.currentWorkingSuborder)\
            or orderID != self.currentWorkingOrder):
            # Ahora crear otro paso que diga que esta suborden fue pausada
            #Saber que mensaje dar
            message = ""
            if(orderID == self.currentWorkingOrder):
                message = f"Switching to suborder {subOrderID}"
            else:
                message = f"Switching to order {orderID}"
            pauseStep = {}
            pauseStep["worker_id"] = self.ID
            pauseStep["step"] = len(self.jsonOutputs[self.currentWorkingOrder]["answer"]["steps"])
            pauseStep["state"] = message
            pauseStep["part_id"] = [self.currentWorkingOrder,self.currentWorkingSuborder]
            pauseStep["time_stamp"] = getTime()
            self.jsonOutputs[self.currentWorkingOrder]["answer"]["steps"].append(pauseStep)
            # Y hagamos el nuevo paso de cooking en la activa
            nextStepID = len(self.jsonOutputs[orderID]["answer"]["steps"])
            step = {}
            step["worker_id"] = self.ID
            step["step"] = nextStepID
            step["state"] = f"cooking stack #{self.shortestOrderIndex} of {numOfTacos} tacos"
            step["part_id"] = [orderID,subOrderID][:]
            step["time_stamp"] = getTime()
            self.jsonOutputs[orderID]["answer"]["steps"].append(step)  
            pass
        # Scenario 3, la orden por completo es pausada
        elif(self.currentWorkingOrder != orderID):
            #Algo me dice que es igual a la previa.....
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
            # queueChalan.put_nowait((self,ingridient,quantity))
            # self.chalanAsignado.queueCabeza.append("lol")
            # Tambien se marca que se pidió, el chalan lo quita de tal listado
            # self.listOfRquestedIngridients.append(ingridient)
        pass

    def spendIngredients(self):
        # Lógica del consumo de ingredientes
        # hastag no se me vino esta idea de aquí https://youtu.be/LwKtRnlongU?t=55
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
                    logging.info("Taquero waits for tortillas :(")
                    while(self.currentTortillas == 0):
                        time.sleep(0.1)
                        self.remainingRestingTime -= 0.1
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
                    logging.info("Taquero waits for salsas :(")
                    while(self.currentSalsa == 0):
                        time.sleep(0.1)
                        self.remainingRestingTime -= 0.1
                    self.currentSalsa -= 1
                self.currentIngridientList.remove("sa")
            elif("gu" in self.currentIngridientList):
                if(self.currentGuacamole > 0):
                    self.currentGuacamole -= 1
                    self.requestIngridient(
                        "gu", self.maxGuacamole-self.currentGuacamole,
                        self.currentGuacamole/self.maxGuacamole)
                else:
                    logging.info("Taquero waits for guacamoles")
                    while(self.currentGuacamole == 0):
                        time.sleep(0.1)
                        self.remainingRestingTime -= 0.1
                    self.currentGuacamole -= 1
                self.currentIngridientList.remove("gu")
            elif("ci" in self.currentIngridientList):
                if(self.currentCilantro > 0):
                    self.currentCilantro -= 1
                    self.requestIngridient(
                        "ci", self.maxCilantro-self.currentCilantro,
                        self.currentCilantro/self.maxCilantro)
                else:
                    logging.info("Taquero waits fot cilantro")
                    while(self.currentCilantro == 0):
                        time.sleep(0.1)
                        self.remainingRestingTime -= 0.1
                    self.currentCilantro -= 1
                self.currentIngridientList.remove("ci")
            elif("ce" in self.currentIngridientList):
                if(self.currentCebolla > 0):
                    self.currentCebolla -= 1
                    self.requestIngridient(
                        "ce", self.maxCebolla-self.currentCebolla,
                        self.currentCebolla/self.maxCebolla)
                else:
                    while(self.currentCebolla == 0):
                        time.sleep(0.1)
                        self.remainingRestingTime -= 0.1
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
            logging.info("Taquero will sort to pick")
            self.sortOrders()
            logging.info("Taquero has sorted and will pick")
            self.shortestOrderIndex = str(list(self.ordenes.keys())[0])
            # Tambien que agarre la lista de ingredientes que se usa x cada taco
            # Explicitamente debe hacerce por valor porque la original debe restaurarse
            #  N tacos por cada stack [:] hace eso
            self.currentIngridientList = self.ordenes[self.shortestOrderIndex][8][:]
            logging.info(
                f"Stack {self.shortestOrderIndex} assigned to work at")
            # Varia por stack, cada x deltas se hace un taco y debemos contarlos
            self.deltasPerTaco = self.ordenes[self.shortestOrderIndex][7] / \
                self.cookUnitDelta
            # acabaste de escojer taquero? ...chido, ahora escribelo en el JSOP
            orderID = self.ordenes[self.shortestOrderIndex][2][0]
            suborderID = self.ordenes[self.shortestOrderIndex][2][1]
            stackID = self.shortestOrderIndex
            ## Sección de codigo exlcuisva del json output
            if(self.currentWorkingOrder == None):
                self.currentWorkingOrder = self.ordenes[self.shortestOrderIndex][2][0]
                self.currentWorkingSuborder = self.ordenes[self.shortestOrderIndex][2][1]
                self.currentWorkingStack = self.shortestOrderIndex
            self.writeOutputSteps(
                "asigned",(orderID,suborderID,stackID)
            )
            self.currentWorkingOrder = self.ordenes[self.shortestOrderIndex][2][0]
            self.currentWorkingSuborder = self.ordenes[self.shortestOrderIndex][2][1]
            self.currentWorkingStack= self.shortestOrderIndex
            ##
        else:
            if(self.shortestOrderIndex == None):
                logging.info(
                    "Taquero is splitting or scheduling, cannot pick  a new index")
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
                        self.deltasPerTaco = self.ordenes[self.shortestOrderIndex][7] / \
                            self.cookUnitDelta
                        # Tambien reiniciar el listado de ingredientes por cada taco
                        #  porque cada taco puede usar 1 ingrediente de cada tipo, no un stack
                        # Aquí tambien debe copiarse por valor y no referencia
                        self.currentIngridientList = self.ordenes[self.shortestOrderIndex][8][:]
                        # Revisar si tiene que descansar una vez que acaba el
                        #   taco y sabe que se hará en el siguiente, o sea
                        #   que al acabar cad a x tacos verá cuanto debe sleep
                        if(self.tacoCounter > 0 and
                                self.tacoCounter % self.tacosRestingThreshold == 0):
                            self.sleepHandler()
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
                    UTIs = self.ordenes[str(headIndex)][0]
                    base = (UTIs ** -1) * 10
                    tax = (
                        UTIs
                        * self.constStarving
                        * (time.time() - self.ordenes[str(headIndex)][3])
                    )
                    self.ordenes[str(headIndex)][1] = (base + tax)
                except Exception as e:
                    logging.error(
                        f"Concurrency error at {self.name}'s  taxer, tried to tax a head in transition to death"
                    )

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
                time.sleep(self.useTimeOfFan)
                logging.info(
                    f"{self.name}'s fan is off"
                )
                deltaA = self.tacoCounter
            # Estar checando cada 0.25  segs, que es un intervalo más
            #  pequeño que le delta de cocina, por lo tanto no *deberia* fallar
            time.sleep(0.20)
        pass


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

    def IngresoPersonal(self, cocina):
        """
        [IDs de taqueros]
            0 -> Adobaba
            1 -> Asada y Suadero (1)
            2 -> Asada y Suadero (2)
            3 -> Tripa y cabeza 
            4 -> El de las quesadillas
        """
        # Aviso: la cocina no puede hacer esto en primer persona
        # (o sea con self), si se hace no pasa nada o pasan comportamientos
        #  no deseados para Omar
        cocina.personal.append(PersonalTaqueria("Omar"))
        cocina.personal[0].chalanAsignado = ChalanTaquero("Julio")
        cocina.personal[0].chalanAsignado.cocinerosAsignados[0] = cocina.personal[0]
        cocina.personal[0].ID = 0
        cocina.personal[0].start()
        cocina.personal[0].chalanAsignado.start()


class CocinaQuesadillero():
    pass


def open_taqueria():
    # Solo poner estas ordenes mientras hacemos pruebas
    ordersToTest = 3
    logging.basicConfig(level=logging.DEBUG, filename="logfile.log", filemode="a+",
                        format="%(asctime)-15s %(levelname)-8s %(message)s")
    Cocina = CocinaTaqueros("Taqueros")
    Cocina.start()
    Cocina.IngresoPersonal(Cocina)

    while(True):
        with open("jsons.json") as OrdenesJSON:
            ListadoOrdenes = json.load(OrdenesJSON)
            for i in range(ordersToTest):
                orden = ListadoOrdenes[i]
                Cocina.personal[0].queue.put(orden)
        time.sleep(999999)
