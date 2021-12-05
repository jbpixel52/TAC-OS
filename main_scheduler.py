import copy
import random
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

ReadingFromDisk = True
abcdario = list(string.ascii_uppercase)
debug_state = True
SAVE_FREQ = 1
EPOCHTIME= datetime.now()
def timeDif():
    return f" T+({(datetime.now()-EPOCHTIME).total_seconds() * 1000:.2f}ms)"
def pureSeconds():
    return   round(((datetime.now()-EPOCHTIME).total_seconds()),ndigits=3)
def getTime():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')

def calculate_asadaANDsuadero_candidate(taqeuro1, taquero2):
    # Funcion que tanto metiendo desde SQS o de disco necesitamos
    #  saber cual de los taqueros dobles (1 y 2) es el mejor para meterle
    #  la orden, no será 50/50 porque si no se duermen a la vez y vale queso
    #  (aunque sería 200% y 0% produccion así qu... ¿no da lo mismo?)
    #  como sea, la intencion es hacerlo uno de alta carga
    #  y otro de baja carga, así (casi) nunca deberia sincronizarse los
    #  descansos
    stacks1 = taqeuro1.ordenes.copy()
    costoUTIs1 = 0
    for stack in stacks1:
        costoUTIs1 += stacks1[stack]["costo utis"]
        
    stacks2 = taquero2.ordenes.copy()
    costoUTIs2 = 0
    for stack in stacks2:
        costoUTIs2 += stacks2[stack]["costo utis"]
        
    # Si ambos estan despiertos se le mete al queue con menos UTIS
    if(not taqeuro1.isResting and not taquero2.isResting):
        if(costoUTIs1/(costoUTIs2+1) > 0.70):
            # Meter al de carga baja si tiene pocas UTIS (<70% aprox)
            return 2
        else: 
            # Si el de carga alta no anda muy cargado le metemos  M A S
            return 1
    # Esta regla se ignora si se está durmiendo el de alta carga
    if(taqeuro1.isResting):
        return 2
    else:
        return 1
        
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
            "adobada": 0,
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
        self.jsonInputs = {}
        self.pointersToOrders = {} # lista de tuplesID que apuntan a sus json outputs, sirve con los quesadilleros
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
        # Exclusivo para logica del uso de los dobles
        # Para poder verificar las UTIs del otro taquero se necesita ver 
        # sus stats de UTIS
        self.pointersToTaquerosDoubles = []
        # quesadillero
        
    def staff_to_json(self):
        while True:
            sleep(SAVE_FREQ)  # HERE WE SET THE SAVING TO DISK INTERVAL e.g., 3 seconds < -
            print(f"- > saving {self.name} at {getTime()} ...")
            self.objects_to_json()

    def objects_to_json(self):
        path = 'logs/staff/taqueros/'+self.name+'.json'
        with open(path, mode='w', encoding='utf-8') as file:
            if(self.chalanAsignado):
                chalan = self.chalanAsignado.name
            else:
                chalan = None
            serialized = {'name': self.name, 'ID': self.ID, 'ordenes': self.ordenes, 'stackcounter': self.stackCounter,
                        'isFanActive': self.isFanActive, 'chalan': chalan, 'cooking': self.Cooking, 'resting': self.isResting, 'Owl': self.isAnOwl,
                        'currentTortillas': self.currentTortillas, 'currentCebolla': self.currentCebolla, 'currentCilantro': self.currentCilantro, 'currentSalsa': self.currentSalsa, 'currentGuacamole': self.currentGuacamole, 'currentWorkingOrder': self.currentWorkingOrder, 'currentWorkingSuborder': self.currentWorkingSuborder}

                
            json.dump(serialized, file, indent=4, sort_keys=True)
            file.close()

    def main(self):
        # Decir que se está en linea
        print(f"Taquero {self.name} en linea")
        # Hacer el templete del output de salidas
        with open("outputs/outputTemplate.json") as jsonSalida:
            self.jsonOutputTemplate = json.load(jsonSalida)

        self.OrderRecieverThread.start()
        self.CookerThread.start()
        self.StarvingTaxerThread.start()
        self.FanThread.start()
        self.saving_memory.start()

    def startOutputtingOrder(self, orden):
        # Funcion que crea un indice en los outputs de salidas
        #  lo hace en base al templete lul
        ordenID = len(self.jsonOutputs)
        absoluteOrderID = ordenID
        absoluteSubOrderID = None
        if(ordenID in self.ordersThatAreNotMine):
            # Cambiar los valores tupleID a reportar en outputs para que sean
            #  los del encargado 
            absoluteOrderID = orden["tupleID"][0]
            absoluteSubOrderID = orden["tupleID"][1]
            pass

        logging.info(f"{self.ID} is outputting input of {ordenID} {timeDif()}")
        # condenado seas python y tu inabilidad de copiar cosas por valor al 100%
        copia = copy.deepcopy(self.jsonOutputTemplate["orderIDGoesHere"])
        self.jsonOutputs[ordenID] = copia
        # Variable que apoya al retorno de ordenes no correspondientes
        if(self.orderCounter not in self.ordersThatAreNotMine):
            self.jsonOutputs[ordenID]["responsable_orden"] = self.ID
        else:
            # Dar el asignado a retornar y recordarle donde va
            self.jsonOutputs[ordenID]['responsable_orden'] = orden["responsable_orden"]
            self.jsonOutputs[ordenID]['tupleID'] = orden['tupleID']
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
            if(ordenID in self.ordersThatAreNotMine):
                self.jsonOutputs[ordenID]['answer']['steps'][suborden]['part_id'] = [
                    absoluteOrderID, absoluteSubOrderID][:]
                self.jsonOutputs[
                    ordenID]['answer']['steps'][suborden]["state"] = f"Suborder {absoluteSubOrderID} arrived at taquero {self.name}"
            else:
                self.jsonOutputs[ordenID]['answer']['steps'][suborden]['part_id'] = [
                    absoluteOrderID, suborden][:]
            
            self.jsonOutputs[ordenID]['answer']['steps'][suborden]['time_stamp'] = getTime(
            )
        pass

    def is_order_rejectable(self, orden):
        for subOrden in orden['orden']:
            if(((subOrden['type'] == "taco") \
                and (subOrden['meat'] in self.allowedMeatTypes) \
                and (subOrden['quantity'] > 0)) 
               or(subOrden['type'] == "quesadilla" 
                  and (subOrden['meat'] in self.allowedMeatTypes or subOrden['meat'] == "")
                  and subOrden['quantity'] > 0)):
                return False
        logging.info(f"order {orden['request_id']} has to be rejected {timeDif()}")
        self.writeOutputSteps("rejectOrder",(orden['request_id'],0,0), None)
        return True
    
    def is_suborder_rejectable(self, orderID, suborden, suborderID):
        if((suborden['type'] in self.allowedOrderTypes) \
            and (suborden['meat'] in self.allowedMeatTypes) \
            and (suborden['quantity'] > 0)
            or(suborden['type'] == "quesadilla" 
                  and (suborden['meat'] in self.allowedMeatTypes or suborden['meat'] == "")
                  and suborden['quantity'] > 0)):
            return False
        else:
            logging.info(f"suborder {suborderID} had to be rejected {timeDif()}")
            self.writeOutputSteps("rejectSuborder",(orderID,suborderID,0), None)
            return True
    
    def send_suborder_somewhere_else(self, suborder, order, numSuborden, QorderID):
        # Qorder ID solo para quesadillero porque esta logica no va 
        #  en el mismo lugar, pero en si es la ID de donde retornar
        # Revisar a donde lo mandaré
        # Mandar solamente la orden con la suborden buena
        # # veces que Omar olvido copiar por valor: >4 xdxd
        ordercopy = copy.deepcopy(order)
        # No se, creo que mi plan era mandar 1 por uno y no por
        #  bonche y de alguna forma me acordé hasta ahora que no lo hice
        #  así pensando que sí, en fin ... arregla esto el sus
        ordercopy['orden'] = []
        ordercopy['orden'].append(suborder) # revaciar la lista para mandar 1 x 1
        #  todo este tiempo ey alfin encontré al (n+noselol)-ultimo sus impostor
        if(suborder["type"] == "taco"):
            indexToSend = self.cocinaDirectory[suborder["meat"]]
        else:
            indexToSend = 4 #Si no es taco directo al de las quesadillas
        if(indexToSend == 1):
            # But first, si esto va dirigido a uno de los taqueros dobles
            # debemos ver cual es el que es el apropiado
            indexToSend = calculate_asadaANDsuadero_candidate(
                self.pointersToTaquerosDoubles[0],
                self.pointersToTaquerosDoubles[1]
                )
            pass
        # # Variable de apoyo en el regreso al taquero encargado para saber donde va
        if(indexToSend != 4):
            ordercopy["tupleID"] = (self.orderCounter,numSuborden)[:]
        else:
            indexToSendToQuesadillero = QorderID
            ordercopy["tupleID"] = (QorderID,numSuborden)[:]
        self.sendQueues[indexToSend].put(ordercopy)

    def splitOrder(self, orden):
        pedido = orden
        numSuborden = 0
        rejectedSubs = []
        ### Primero reviso si toda la orden es rechazable
        if(self.is_order_rejectable(orden)):
            # Subir el contador de orden + 1 pero no registrarlo
            self.orderCounter += 1
            #self.pointersToOrders[self.orderCounter] = len(self.jsonOutputs)
            pass
        else: # Si la orden entera no era rechazable, procedamos
            # Seccionar en partes la orden (los indices de ['orden'])
            self.jsonInputs[self.orderCounter] = orden
            self.pointersToOrders[self.orderCounter] = len(self.jsonInputs)-1
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
                    if((subOrden["meat"] not in self.meatTypes and subOrden["type"] != "quesadilla")):
                        if(self.ID != 4): # el quesadillero recibe de forma segura las ordenes (subs)
                            # se permiten quesadillas sin carne
                            #Tanto en output como en logica pondre el encargado
                            pedido["responsable_orden"] = self.ID
                            self.send_suborder_somewhere_else(subOrden, pedido, numSuborden, None) 
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
                        if(subOrden['type'] == "quesadilla" and subOrden['meat'] == ""):
                            costoUTIs = 0
                            tiempoParaCocinar = 0
                        else:
                            if(self.ID != 4):
                                # no pagar carne si no se pone
                                costoUTIs = 1
                                tiempoParaCocinar = 1
                            else:
                                # no paga el de quesadillas
                                costoUTIs = 0
                                tiempoParaCocinar = 0
                        subSplitIndex = 0
                        # Variable que dice sí es quesadilla o no
                        isQuesadilla = False
                        if(subOrden['type'] == "quesadilla"):
                            isQuesadilla = True
                        # Variables relacionadas con el uso de ingredientes
                        #  recordatorio: si una suborden usa x ingrediente, sus stacks tambien
                        #  y siempre se usan tortillas lol (to = *to*rtillas)
                        listaIngridients = ["", "", "", "", "to"]
                        # Los taqueros pagan ingredientes
                        if(True): # no se que pasará si lo quito, no hay tiempo para pensar
                            # Hacer un calculo del costo
                            if(self.ID == 4):
                                costoUTIs += 20
                                tiempoParaCocinar += 20
                                pass
                            else:      
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
                                    "arrival time": pureSeconds(),
                                    "quantity": subOrden['quantity'],
                                    "individual cost": costoUTIsIndividual,
                                    "time to cook": tiempoParaCocinar,
                                    "indiv. time to cook": tiempoCocinarIndividual,
                                    "ingridient list": listaIngridients,
                                    "isQuesadilla": isQuesadilla
                                }
                                logging.info(
                                    f"Stack {self.stackCounter} has been put in {self.ID}'s head {timeDif()}")
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
                                    ##tacosSobrantes = 1
                                    ##tacosPorStack -= 1
                                    # bueno, ya lo rompí, no duerno hasta arreglarlo 
                                    #  por las malas...
                                    pass
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
                                        "arrival time": pureSeconds(),
                                        "quantity": tacosSobrantes,
                                        "individual cost": costoUTIsIndividual,
                                        "time to cook": residuoTiempo,
                                        "indiv. time to cook": tiempoCocinarIndividual,
                                        "ingridient list": listaIngridients,
                                        "isQuesadilla": isQuesadilla
                                    }
                                    logging.info(
                                        f"Stack {self.stackCounter} has ben put in {self.ID}'s head {timeDif()}")
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
                                        "costo utis": costoStack,
                                        "prioridad": prioridad,
                                        "tupleID": (self.orderCounter, numSuborden, subSplitIndex),
                                        "arrival time": pureSeconds(),
                                        "quantity": tacosPorStack,
                                        "individual cost": costoUTIsIndividual,
                                        "time to cook": tiempoParaCocinar,
                                        "indiv. time to cook": tiempoCocinarIndividual,
                                        "ingridient list": listaIngridients,
                                        "isQuesadilla": isQuesadilla
                                    }
                                    logging.info(
                                        f"Stack {self.stackCounter} has ben put in {self.ID}'s head {timeDif()}")
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

    def fuse_order(self, orderToFuse):
        # Objetivo de esta funcion es mezclar los pasos de la orden
        # retornada, tambien debe haber revision de finalizacion
        # Marcar como completa la suborden en el diccionario de subordenes
        #  completas de ordenes
        orderID = orderToFuse["tupleID"][0]
        suborderID = orderToFuse["tupleID"][1]
        self.ordenesSuborders[orderID][suborderID][1] = 1
        answerStepsToGive = copy.deepcopy(orderToFuse["answer"]["steps"])
        answerStepsToRecieve = copy.deepcopy(self.jsonOutputs[orderID]["answer"]["steps"])
        answerStepsToRecieve += answerStepsToGive
        answerStepsToRecieve = sorted(answerStepsToRecieve, key = lambda date:datetime.strptime(date['time_stamp'], '%Y-%m-%d %H:%M:%S.%f'))
        # Rehacer el orden de los pasos
        for step in range(len(answerStepsToRecieve)):
            answerStepsToRecieve[step]['step'] = step
        # Reinsertar los pasos en el output
        self.jsonOutputs[orderID]["answer"]["steps"] = answerStepsToRecieve
        # Revisar que la orden esté finalizada
        self.checkOrderCompletion(orderID)
        # Arregla el bug que ordenes de retorno se no marcaban como completas
        self.finisherOutput("order", (orderID, 0, 0))
        
    def process_order(self, newOrder, returned):
        if(not returned):
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
                    f"{self.name} ha finalizado la particion y organización de orden {self.orderCounter-1} {timeDif()}")
            except Exception as e:
                logging.exception(
                    f"Error en el sorting de ordenes - > {Exception}")
        else:
            # Si es una orden de retorno ya fue cocinada, metamosla devuelta
            #  en su output correspondiende
            logging.info(f"{self.ID} has recieved a completed order by someone else")
            self.fuse_order(newOrder)
    
    def recieveOrders(self):
        while(True):
            logging.debug(self.ordenes)
            logging.info(self.ordenesSuborders)
            logging.info(f"{self.name}'s headsofOrders:{self.ordenesHeads} {timeDif()}")
            logging.info(f"{self.name}'s taco counter: {self.tacoCounter} {timeDif()}")
            logging.info(
                f"{self.name}'s remaining ingridients:{self.currentSalsa}|{self.currentGuacamole}|{self.currentCilantro}|{self.currentCebolla}|{self.currentTortillas} {timeDif()}"
            )
            logging.info(
                f"Taquero {self.name} stats: OC:{self.orderCounterCompleted}|SOC:{self.subOrderCounter}|STC:{self.stackCounterCompleted}|TC:{self.tacoCounter} {timeDif()}")
            # Placeholder de output json
            with open(f"outputs/outputs_id_{self.ID}.json", "w") as outputs:
                json.dump(self.jsonOutputs, outputs,indent=4,sort_keys=True)
            # Placeholder end
            # Las ordenes se procesan a lo dos máximo cada delta
            if(not self.recieveQueue.empty()):
                self.ordersThatAreNotMine.append(self.orderCounter)
                self.process_order(self.recieveQueue.get_nowait(), False)
            if(not self.queue.empty()):
                self.process_order(self.queue.get_nowait(), False)
            # tres si cuentas el recibir ordenes de retorno, dejemoslo en 2 + 1
            if(not self.recieveQueueReturn.empty()):
                self.process_order(self.recieveQueueReturn.get_nowait(), True)
            # Arregla bug que no se piden ingredientes cuando se hace nada
            # o era intención de Omar y no se acuerda? hmmm... 
            #  ustedes que dicen, ¿era bug o feature?  
            self.checkIngridients()
            # if debug_state is True:
            time.sleep(self.ordersPerSecondDelta)

    def sleep_handler(self):
        if(not self.isAnOwl):
            if(self.remainingRestingTime <= 0):
                # Si hubo muchos hangups, entonces hubo mucho descanso y no es
                #  necesario otro descanso, asi que solo se reinicia el contador
                logging.info(
                    f"Taquero {self.name} has already rested too much so he won't {timeDif()}"
                )
                self.writeOutputSteps(
                    "noSleep", self.ordenes[self.shortestOrderIndex]["tupleID"], None)
                pass
            else:
                logging.info(
                    f"Taquero {self.name} must rest {self.remainingRestingTime} seconds {timeDif()}"
                )
                self.writeOutputSteps(
                    "yesSleep", self.ordenes[self.shortestOrderIndex]["tupleID"], None)
                self.isResting = True
                time.sleep(self.remainingRestingTime)
                self.isResting = False
                logging.info(f"Taquero {self.name} has rested {timeDif()}")
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
                f"{self.name}'s order {orderToCheckIndex} is complete {timeDif()}")
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
                       == self.ordenes[self.shortestOrderIndex]["tupleID"][0]
                       and self.ordenes[str(int(self.shortestOrderIndex)+1)]["tupleID"][1]
                       == self.ordenes[self.shortestOrderIndex]["tupleID"][1]):
                        # Sí el siguiente taco counter comparte el mismo
                        # padre/inicio entonces hacer el venico la nueva
                        # cabeza al acabar este stack
                        # Omar: se supone que la cabeza solo se pasaba a 
                        # otros stacks de la sub, raro...
                        # si esto no lo arregla las cosas se pondran feo
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
                        # Acabaste, pero era una quesadilla? si no, solo falta
                        #  pagar el queso, amdaselo al de las quesadillas para
                        #  que lo acabe
                        if(not self.ordenes[self.shortestOrderIndex]['isQuesadilla']
                           or self.ID == 4):
                            if(self.ID == 4):
                                x = 5
                            # quesadillero excepcion a esa regla
                            self.subOrderCounter += 1
                            # Declarar en el registro de subordenes de ordenes
                            #   su completación (completición?)
                            self.ordenesSuborders[orderToCheckIndex
                                                ][subOrderToEndIndex][1] = 1
                            # self.finisherOutput("subOrder", (orderToCheckIndex, subOrderToEndIndex, 0))
                            logging.info(
                                f"{self.name}'s suborder {self.subOrderCounter} completed {timeDif()}")
                            finishedASubOrder = True
                            # Revisar si se acabó la orden
                            finishedAnOrder = self.checkOrderCompletion(
                                orderToCheckIndex
                            )
                            # Revisar si se acabó la orden
                        else:
                            # Mandar al de las quesadillas para que cierre el
                            # trato
                            # Mandar al de las quesadillas para que cierre el
                            # trato, hay que extraer la orden de los inputs
                            tupleID = self.ordenes[self.shortestOrderIndex]["tupleID"]
                            QorderID = tupleID[0]
                            subroderIndex = tupleID[1]
                            inputIndex = self.pointersToOrders[tupleID[0]]
                            order = self.jsonInputs[inputIndex]
                            subOrder = order['orden'][subroderIndex]
                            order["responsable_orden"] = self.ID
                            self.send_suborder_somewhere_else(subOrder, order, subroderIndex, QorderID)
                else:
                    # Si el ultimo elemento cocinado (en algun insante)
                    # era una cabeza que no pudo ser removida, la
                    # intentamos quitar
                    if(int(self.shortestOrderIndex) in self.ordenesHeads):
                        self.ordenesHeads.remove(
                            int(self.shortestOrderIndex))
                    if(not self.ordenes[self.shortestOrderIndex]['isQuesadilla']
                           or self.ID == 4):
                        if(self.ID == 4):
                            x = 5
                        self.subOrderCounter += 1
                        # Cada removida de cabeza sin remplazarla == se acabó el stack
                        #self.subOrderCounter += 1
                        # Declarar que suborden x de orden y se acabó
                        self.ordenesSuborders[orderToCheckIndex
                                            ][subOrderToEndIndex][1] = 1
                        # self.finisherOutput("subOrder", (orderToCheckIndex, subOrderToEndIndex, 0))
                        logging.info(
                            f"{self.name}'s suborder {self.subOrderCounter} completed {timeDif()}")
                        finishedASubOrder = True
                        # Revisar si se acabó la orden
                        finishedAnOrder = self.checkOrderCompletion(
                            orderToCheckIndex)
                    else:
                        # Mandar al de las quesadillas para que cierre el
                        # trato, hay que extraer la orden de los inputs
                        tupleID = self.ordenes[self.shortestOrderIndex]["tupleID"]
                        QorderID = tupleID[0]
                        subroderIndex = tupleID[1]
                        inputIndex = self.pointersToOrders[tupleID[0]]
                        order = self.jsonInputs[inputIndex]
                        subOrder = order['orden'][subroderIndex]
                        order["responsable_orden"] = self.ID
                        self.send_suborder_somewhere_else(subOrder, order, subroderIndex, QorderID)
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
                    f"{self.name}'s stack {self.shortestOrderIndex} completed {timeDif()}")

                self.shortestOrderIndex = None

    def finisherOutput(self, type, tupID):
        # Primero reviso si esta orden es mía, si no no hago
        # esto y le mando devuelta al taquero normal
        orderID = tupID[0]
        subOrderID = tupID[1]
        stackID = tupID[2]
        absoluteOrderID = orderID
        absoluteSubOrderID = subOrderID
        if(orderID in self.ordersThatAreNotMine):
            # Usar el tupleID del encargado, no el relativo
            absoluteOrderID = self.jsonOutputs[orderID]["tupleID"][0]
            absoluteSubOrderID =  self.jsonOutputs[orderID]["tupleID"][1]
        nextStepID = len(self.jsonOutputs[orderID]["answer"]["steps"])
        step = {}
        step["worker_id"] = self.ID
        step["step"] = nextStepID
        step["state"] = None
        step["part_id"] = [absoluteOrderID, absoluteSubOrderID][:]
        step["time_stamp"] = getTime()
        if(type == "order"):
            step["state"] = f"Order {orderID} complete"
            self.jsonOutputs[orderID]["status"] = "complete"
        elif(type == "subOrder"):
            step["state"] = f"Suborder {absoluteSubOrderID} complete"
        else:
            step["state"] = f"Stack#{stackID}({self.shortestOrderIndex}) complete"
        if(orderID in self.ordersThatAreNotMine and type=="order"):
            pass # El paso de acabar solo lo hace el encargado
        else:
            self.jsonOutputs[orderID]["answer"]["steps"].append(step)
        # Hacer una copia de esta orden en el output para mandarla al encargado
        # y borrarlo de mi parte, pero solo sí se acaba la orden
        if(orderID in self.ordersThatAreNotMine 
                and type == "order"):
            orderToReturn = copy.deepcopy(self.jsonOutputs[orderID])
            self.jsonOutputs[orderID] = "This index is now somewhere else, Omar will tell you where is he does not snap"
            # Ubicar a que queue se le debe regresar la orden
            # Todas las subs son iguales así que solo hay que revisar 1
            indexToReturnTo = orderToReturn["responsable_orden"]
            self.sendQueuesReturn[indexToReturnTo].put(orderToReturn)
        if(orderID not in self.ordersThatAreNotMine and not ReadingFromDisk):
            orderToReturnToSqs = self.jsonOutputs[orderID]
            pass # Aquí se pone denuevo en el SQS la orden
            
    def writeOutputSteps(self, action, tupleID, extraArg):
        orderID = tupleID[0]
        subOrderID = tupleID[1]
        stackID = tupleID[2]
        absoluteOrderID = orderID 
        absoluteSubOrderID = subOrderID
        if(orderID in self.ordersThatAreNotMine):
            # Cambiar los valores tupleID a reportar en outputs para que sean
            #  los del encargado 
            absoluteOrderID = self.jsonOutputs[orderID]["tupleID"][0]
            absoluteSubOrderID = self.jsonOutputs[orderID]["tupleID"][1]
            pass
        ## Revisar si no es mia la orden para cambiar la ID y subID
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
                if(not isinstance(self.jsonOutputs[self.currentWorkingOrder],str)):
                    # Asumo que lo que debería decir es esto:a
                    #  si ya se fue la orden no digo que cambiaré a otra
                    #   si es un string, ya se fue
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
            step["part_id"] = [absoluteOrderID, absoluteSubOrderID][:]
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
            step["part_id"] = [absoluteOrderID, absoluteSubOrderID][:]
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
            step["part_id"] = [absoluteOrderID, absoluteSubOrderID][:]
            step["time_stamp"] = getTime()
            self.jsonOutputs[orderID]["answer"]["steps"].append(step)
            pass
        pass

    def requestIngridient(self, ingridient, quantity, priority):
        if(self.ID == 4):
            if(quantity == 0):
                time.sleep(5)
                self.currentTortillas = self.maxTortillas
            else:
            # el quesadillero solo necesita tortillas
            # correle a la tienda cada que hagas cinco!!!
                pass
        else:
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
                    logging.info(f"Taquero {self.ID} waits for tortillas :( {timeDif()}")
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
                    logging.info(f"Taquero {self.ID} waits for salsas :( {timeDif()}")
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
                    logging.info(f"Taquero {self.ID} waits for guacamoles {timeDif()}")
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
                    logging.info(f"Taquero {self.ID} waits fot cilantro {timeDif()}")
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
                    logging.info(f"Taquero {self.ID} waits fot cebollas {timeDif()}")
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
            if(self.ID == 2):
                x = 5
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
            if((self.currentTortillas != self.maxTortillas) and ("to" not in self.listOfRquestedIngridients)):
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
            logging.info(f"Taquero {self.name} will sort to pick {timeDif()}")
            self.sortOrders()
            logging.info(f"Taquero {self.name} has sorted and will pick {timeDif()}")
            self.shortestOrderIndex = str(list(self.ordenes.keys())[0])
            # Tambien que agarre la lista de ingredientes que se usa x cada taco
            # Explicitamente debe hacerce por valor porque la original debe restaurarse
            #  N tacos por cada stack [:] hace eso
            self.currentIngridientList = self.ordenes[self.shortestOrderIndex]["ingridient list"].copy()
            logging.info(
                f"{self.name} current working stack is now: {self.shortestOrderIndex} {timeDif()}")
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
                    f"Taquero {self.name}is splitting or scheduling, cannot pick  a new index {timeDif()}")
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
                    #logging.error(
                     #   f"Concurrency error at {self.name}'s  taxer, tried to tax a head in transition to death"
                    #)
                    pass # hora de la almmohada muchacho

            if debug_state is True:
                time.sleep(1.0)

    def sortOrders(self):
        logging.info(f"Sorting start {timeDif()}")
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
        logging.info(f"Sorting end {timeDif()}")
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
                    f"{self.name}'s fan has been activated at a TC of {self.tacoCounter} {timeDif()}"
                )
                try:
                    self.writeOutputSteps(
                        "fanON", self.ordenes[self.shortestOrderIndex]["tupleID"], None)
                except Exception as e:
                    logging.error(f"My fan was turned on while not cooking {timeDif()}")
                time.sleep(self.useTimeOfFan)
                logging.info(
                    f"{self.name}'s fan is off"
                )
                try:
                    self.writeOutputSteps(
                        "fanOFF", self.ordenes[self.shortestOrderIndex]["tupleID"], None)
                except Exception as e:
                    logging.error(f"My fan was turned off while not cooking {timeDif()}")
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
            f"Chalan will go to the store for {orderTypeToRefill} {timeDif()}")
        time.sleep(timeToRefill)
        if(taqueroIDToRefill == 3 or taqueroIDToRefill == 0):
            taqueroIDToRefill = 0 # 0 y 3 son 0, 1 y 2 son 1
        else:
            taqueroIDToRefill = 1
            #esto resuleve el bug de que se me olvidó poner el else
            # dato chido: tambien habia otro bug que hacia siempre pedir tortillas
            # porque en check ingridients comparaba con la cebolla
            pass
        if(orderTypeToRefill == "to"):
            self.cocinerosAsignados[taqueroIDToRefill].currentTortillas += quantityToRefill
            # Decirle al taquero que ya le dio los ingredientes solicitados
            self.cocinerosAsignados[taqueroIDToRefill].listOfRquestedIngridients.remove(
                "to")
            logging.info(
                f"Chalan returned and has given {quantityToRefill} tortillas to taquero {taqueroIDToRefill} {timeDif()}")
        elif(orderTypeToRefill == "sa"):
            self.cocinerosAsignados[taqueroIDToRefill].currentSalsa += quantityToRefill
            self.cocinerosAsignados[taqueroIDToRefill].listOfRquestedIngridients.remove(
                "sa")
            logging.info(
                f"Chalan returned and has given {quantityToRefill} salsas to taquero {taqueroIDToRefill} {timeDif()}")
        elif(orderTypeToRefill == "gu"):
            self.cocinerosAsignados[taqueroIDToRefill].currentGuacamole += quantityToRefill
            self.cocinerosAsignados[taqueroIDToRefill].listOfRquestedIngridients.remove(
                "gu")
            logging.info(
                f"Chalan returned and has given {quantityToRefill} guacamoles to taquero {taqueroIDToRefill} {timeDif()}")
        elif(orderTypeToRefill == "ci"):
            self.cocinerosAsignados[taqueroIDToRefill].currentCilantro += quantityToRefill
            self.cocinerosAsignados[taqueroIDToRefill].listOfRquestedIngridients.remove(
                "ci")
            logging.info(
                f"Chalan returned and has given {quantityToRefill} cilantros to taquero {taqueroIDToRefill} {timeDif()}")
        elif(orderTypeToRefill == "ce"):
            self.cocinerosAsignados[taqueroIDToRefill].currentCebolla += quantityToRefill
            self.cocinerosAsignados[taqueroIDToRefill].listOfRquestedIngridients.remove(
                "ce")
            logging.info(
                f"Chalan returned and has given {quantityToRefill} cebollas to taquero {taqueroIDToRefill} {timeDif()}")
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
            whereitCameFrom = 0
            # Escucha ambas solicitudes y luego decide irse o no a la tienda y rellenar
            if(self.queueA.empty()):
                pass
            else:
                # Si hubo una solicitud de rellenar que lo lea del pizarron, que se lo meta en su cabeza
                while(not self.queueA.empty()):
                    self.priorityQueueCabeza.append(self.queueA.get_nowait())
                    whereitCameFrom = 0
            pass
            if(self.queueB.empty()):
                pass
            else:
                while(not self.queueB.empty()):
                    self.priorityQueueCabeza.append(self.queueB.get_nowait())
                    whereitCameFrom = 1
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
                if(taqueroIDToRefill == 2):
                    x = 5
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
        self.current70 = 1 # Taquero al que se le manda el 70% de la carga

        pass

    def main(self):
        print("Cocina encendida")
        print(
            "Puente hacia el disco casi abierto lol #$%^& Windows y su falta de fork()")
        
    def ingreso_personal(self, cocina):
        listOfNames = ["Omar","Marcelino","Jose","Jerry","Carlos"]
        """
        [IDs de taqueros]
            0 - > Adobaba
            1 - > Asada y Suadero (1)
            2 - > Asada y Suadero (2)
            3 - > Tripa y cabeza 
            4 - > El de las quesadillas [used?]
        """
        # Aviso: la cocina no puede hacer esto en primer persona
        # (o sea con self), si se hace no pasa nada o pasan comportamientos
        #  no deseados para Omar
        # El queue send de uno es el receptor de otro y viceversa
        for i in range(5):
            # Asignacion de espacios vacios, nombres de personal y ID
            cocina.personal.append(None)
            cocina.personal[i] = PersonalTaqueria(str(listOfNames[i]))
            cocina.personal[i].ID = i
            
        chalanA = ChalanTaquero("Julio")
        chalanB = ChalanTaquero("Adan")
        # Asignación de Chalanes
        cocina.personal[0].chalanAsignado = cocina.personal[1].chalanAsignado = chalanA
        cocina.personal[2].chalanAsignado = cocina.personal[3].chalanAsignado = chalanB
        
        #Asignación de los 4 tipos de carnes
        cocina.personal[0].meatTypes = ["adobada"]
        cocina.personal[1].meatTypes = ["asada","suadero"]
        cocina.personal[2].meatTypes = ["asada","suadero"]
        cocina.personal[3].meatTypes = ["tripa","cabeza"]
        cocina.personal[4].meatTypes = ["tripa","cabeza","asada","suadero","adobada"] # en realidad no las usa pero erá mas facil poner esto
        
        #Asignarle a los chalanes sus taqueros correspondientes
        # el 0 es para los solitarios y el 1 es para los paralelos (asada y suadero)
        # mejor los llamo dobles..
        cocina.personal[0].chalanAsignado.cocinerosAsignados[0] = cocina.personal[0]
        cocina.personal[1].chalanAsignado.cocinerosAsignados[1] = cocina.personal[1]
        cocina.personal[2].chalanAsignado.cocinerosAsignados[1] = cocina.personal[2]
        cocina.personal[3].chalanAsignado.cocinerosAsignados[0] = cocina.personal[3]
        
        
        for i in range(5):
            for j in range(5):
                cocina.personal[i].sendQueues.append(None)
                cocina.personal[i].sendQueuesReturn.append(None)

        # Asignar buses de envio y recibo de ordenes
        #  caminos recpetores de ordenes no correspondientes
        #  y receptor de retorno de ordenes terminadas que no eran correspondientes
        for i in range(5):
            cocina.personal[i].recieveQueue = Queue()
            cocina.personal[i].recieveQueueReturn = Queue()

        # Asignar queues de envio de ordenes no correspondientes
        for i in range(0,5):   
            for j in range(0,5):
                #Si, tecnicamente le estamos metiendo su propio queue
                # como un sendqueue, pero eso era más facil que modifcar el for
                cocina.personal[j].sendQueues[i] =  cocina.personal[i].recieveQueue
            
        
        # Asignar queues de envio de retorno de ordenes no correspondientes
        for i in range(0,5):   
            for j in range(0,5):
                #Si, tecnicamente le estamos metiendo su propio queue
                # como un sendqueue, pero eso era más facil que modifcar el for
                cocina.personal[j].sendQueuesReturn[i] =  cocina.personal[i].recieveQueueReturn
        
        # Dar apuntadores (voy a ir con la finta que python está haciendo
        #  esto por referencia) de los taqueros dobles a todos
        #  ellos son dos personas, IDs 1 y 2
        for i in range(5):
            cocina.personal[i].pointersToTaquerosDoubles.append(
                cocina.personal[1]
            )
            cocina.personal[i].pointersToTaquerosDoubles.append(
                cocina.personal[2]
            )
        # Arrancar los threads de cocineros y sus chalanes
        #  una vez que todos sus datos estan asignados
        for i in range(5):       
            cocina.personal[i].start()
        cocina.personal[0].chalanAsignado.start()
        cocina.personal[3].chalanAsignado.start()
            
def open_taqueria():
    # Solo poner estas ordenes mientras hacemos pruebas
    ordersToTest = 6
    ordersToTest2 = 5
    ordersToTest3 = 4
    # si se desean ver ordenes en cabeza, cambiar nivel a debug
    logging.basicConfig(level=logging.DEBUG, filename="logfile.log", filemode="w",
                        format="%(asctime)s - [%(levelname)s] - [%(threadName)s] - %(name)s - (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s")
    Cocina = CocinaTaqueros("Taqueros")
    Cocina.start()
    Cocina.ingreso_personal(Cocina)

   
    
    while(True):
        if(ReadingFromDisk):
            with open("queuesDisco/jsonOmar.json") as OrdenesJSON:
                ListadoOrdenes = json.load(OrdenesJSON)
                for i in range(ordersToTest):
                    orden = ListadoOrdenes[i]
                    Cocina.personal[0].queue.put(orden)
            with open("queuesDisco/jsonJerry.json") as OrdenesJSON:
                ListadoOrdenes = json.load(OrdenesJSON)
                for i in range(ordersToTest2):
                    orden = ListadoOrdenes[i]
                    Cocina.personal[3].queue.put(orden)
            with open("queuesDisco/jsonDouble.json") as OrdenesJSON:
                ListadoOrdenes = json.load(OrdenesJSON)
                for i in range(ordersToTest3):
                    # indexToGive = Cocina.calculate_asadaANDsuadero_candidate(Cocina)
                    # Si uno duerme, el otro toma control
                    if(Cocina.personal[1].isResting):
                        indexToGive = 2
                    else:
                        indexToGive = 1
                    # print(f"The best index to send to doubles are {indexToGive}")
                    orden = ListadoOrdenes[i]
                    Cocina.personal[indexToGive].queue.put(orden)         
            time.sleep(999999) # <- recordatorio para Omar -> DEJALO COMO ESTABA
        else:
            orderMessageFromSQS = None
            queueToPut = random.randint(0,3)
            if(queueToPut == 1 or queueToPut ==2):
                if(Cocina.personal[1].isResting):
                    queueToPut = 2
                else:
                    queueToPut = 1
            else:
                pass
            Cocina.personal[indexToGive].queue.put(orderMessageFromSQS) 
            # Aquí se borra el mensaje recibido 
            
