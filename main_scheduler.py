import multiprocessing
from queue import Empty
import queue
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
        self.emojis = ''
        self.ID = 0
        # Variables MUTEX
        self.Splitting = False
        self.Rescheduling = False
        self.Cooking = False
        # Esctructuras de datos
        # Cuaderno con los jsons de entrada (se usará?)
        self.cuadernilloRecibidos = {}
        self.cuadernilloSalidas = {}  # Cuadrerno con los jsons de salida
        self.ordenes = {}  # dict in mind per worker
        self.ordenesHeads = []  # lista con las cabezas de subordenenes
        # Variables
        self.ordersPerSecondDelta = 3  # ^-1
        self.cookUnitDelta = 0.5  # Minimo para cocinar
        self.tacoCounter = 0
        self.orderCounter = 0
        # Antes conocido como tacoCounter (incorrectamente)
        self.stackCounter = 0
        self.deltasPerTaco = 0  # Definida por el thread cooker, varia por stack
        self.constMagnitud = 40  # ya no es p90 lol, ni para 4 tacos con todo alcanzaba
        # blah blah + [utis*const*tiempoatrasado], consultar desmos para demo
        self.constStarving = 0.005
        self.shortestOrderIndex = None  # Una vez inicia un stack no lo detiene
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
        # Chalan asignado, lo asigna la clase cocina
        self.chalanAsignado = None
        # Lista de variables que especifican que ya se solicitó un rellenado
        #  de ingredientes, el chalan se encarga de quitarlos de tal lista
        self.listOfRquestedIngridients = []

    def main(self):
        # Decir que se está en linea
        print(f"Taquero {self.name} en linea")
        self.OrderRecieverThread.start()
        self.CookerThread.start()
        self.StarvingTaxerThread.start()

    def taquitos_emojis(self):
        print(f"ORDENES:", end='')
        self.emojis = ':taco: ' * len(self.ordenes)
        print(emoji.emojize(self.emojis))
        self.emojis = ''

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
                        f"Stack {self.stackCounter} has ben put ahead")
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
        self.orderCounter += 1
        pass

    def recieveClientOrders(self):
        while(True):
            logging.info(self.ordenes)
            logging.info(f'HeadsofOrders:{self.ordenesHeads}')
            logging.info(f"Taco counter: {self.tacoCounter}")
            logging.info(
                f"Remaining ingridients:{self.currentSalsa}|{self.currentGuacamole}|{self.currentCilantro}|{self.currentCebolla}|{self.currentTortillas}"
            )
            if(self.queue.empty()):
                pass
            else:
                newOrder = self.queue.get_nowait()
                self.cuadernilloRecibidos[str(self.tacoCounter)] = newOrder
                logging.info("Iniciando particion de orden x")
                self.Splitting = True
                self.SplitOrder(newOrder)
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

    def requestIngridient(self, ingridient, quantity):
        if(ingridient not in self.listOfRquestedIngridients):
            # Si no está el ingrediente en la lista de solicitados, se pide
            queueChalan = self.chalanAsignado.queueA
            queueChalan.put((ingridient, quantity, self.ID))
            # queueChalan.put_nowait((self,ingridient,quantity))
            # self.chalanAsignado.queueCabeza.append("lol")
            # Tambien se marca que se pidió, el chalan lo quita de tal listado
            self.listOfRquestedIngridients.append(ingridient)
        pass

    def spendIngredients(self):
        # Lógica del consumo de ingredientes
        # hastag no se me vino esta idea de aquí https://youtu.be/LwKtRnlongU?t=55
        if("to" in self.currentIngridientList):
            # Revisar si en la orden en la lista ingredientes se usa un ingrediente
            if(self.currentTortillas > 0):
                # Si se tiene se gasta
                self.currentTortillas -= 1
                # Solicitar ingrediente
                self.requestIngridient(
                    "to", self.maxTortillas-self.currentTortillas)
            else:
                # Si no se espera hasta que le llegue (temporal esta forma)
                logging.info("Taquero waits for tortillas :(")
                while(self.currentTortillas == 0):
                    time.sleep(0.1)
                # Una vez llega sigue trabajando
                self.currentTortillas -= 1
            # quitarlo de la lista al fin de todo modo
            self.currentIngridientList.remove("to")
        elif("sa" in self.currentIngridientList):
            if(self.currentSalsa > 0):
                self.currentSalsa -= 1
                self.requestIngridient("sa", self.maxSalsa-self.currentSalsa)
            else:
                while(self.currentSalsa == 0):
                    time.sleep(0.1)
                self.currentSalsa -= 1
            self.currentIngridientList.remove("sa")
        elif("gu" in self.currentIngridientList):
            if(self.currentGuacamole > 0):
                self.currentGuacamole -= 1
                self.requestIngridient(
                    "gu", self.maxGuacamole-self.currentGuacamole)
            else:
                while(self.currentGuacamole == 0):
                    time.sleep(0.1)
                self.currentGuacamole -= 1
            self.currentIngridientList.remove("gu")
        elif("ci" in self.currentIngridientList):
            if(self.currentCilantro > 0):
                self.currentCilantro -= 1
                self.requestIngridient(
                    "ci", self.maxCilantro-self.currentCilantro)
            else:
                while(self.currentCilantro == 0):
                    time.sleep(0.1)
                self.currentCilantro -= 1
            self.currentIngridientList.remove("ci")
        elif("ce" in self.currentIngridientList):
            if(self.currentCebolla > 0):
                self.currentCebolla -= 1
                self.requestIngridient(
                    "ce", self.maxCebolla-self.currentCebolla)
            else:
                while(self.currentCebolla == 0):
                    time.sleep(0.1)
                self.currentCebolla -= 1
            self.currentIngridientList.remove("ce")

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
                if(not self.Rescheduling and not self.Splitting and self.shortestOrderIndex != None):
                    # Esta variable la vamos a usar?....
                    self.Cooking = True
                    # La delta ahora se hace primero para evitar reporte
                    # prematura de completicion de stack
                    # if debug_state is True:
                    time.sleep(self.cookUnitDelta)
                    # Gastar ingredientes
                    self.spendIngredients()
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

                    # Lógica de restar tiempo, quitar cabezas y hacer pop
                    # Ver si le queda tiempo por cocinar al stack, si no quitarlo
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
        self.queueCabeza = []
        pass

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
                # Si hubo una solicitud de rellenar que lo lea del pizarron y se lo meta en su cabeza
                self.queueCabeza.append(self.queueA.get_nowait())
            pass
            if(self.queueB.empty()):
                pass
            else:
                # Si hubo una solicitud de rellenar que lo lea del pizarron y se lo meta en su cabeza
                self.queueCabeza.append(self.queueB.get_nowait())
            pass
            # Decidir si tiene que rellenar algo en base a la solicitud más reciente
            if(len(self.queueCabeza) > 0):
                quantityToRefill = self.queueCabeza[0][1]
                taqueroIDToRefill = self.queueCabeza[0][2]
                if(self.queueCabeza[0][0] == "to"):
                    timeToRefill = 5
                    orderTypeToRefill = "to"
                    pass
                pass
            else:
                # Si no hay ordenes entonces que siga estando al tanto
                pass

            if(len(self.queueCabeza) > 0):
                # Imprimir la lista de solicitudes si no está vacia
                logging.info(self.queueCabeza)
                # Hacer el relleno yendo a la tienda
                logging.info(
                    f"Chalan will go to the store for {orderTypeToRefill}")
                time.sleep(timeToRefill)
                if(orderTypeToRefill == "to"):
                    Cocina.personal[taqueroIDToRefill].currentTortillas += quantityToRefill
                    # Decirle al taquero que ya le dio los ingredientes solicitados
                    Cocina.personal[taqueroIDToRefill].listOfRquestedIngridients.remove(
                        "to")
                    logging.info(
                        f"Chalan returned and has given {quantityToRefill} tortillas to taquero {taqueroIDToRefill}")
                # Remover de su queue de cabeza esa tarea
                self.queueCabeza.pop(0)

            # Volver a revisar los pizarrones, necesario ese sleep?
            time.sleep(0.25)
        pass


class CocinaTaqueros(multiprocessing.Process):
    def __init__(self, _name):
        # SuperConsteructor
        super(CocinaTaqueros, self).__init__(target=self.main, name=_name)
        self.personal = []

    def main(self):
        print("Cocina encendida")

    def IngresoPersonal(self, cocina):
        """
        [IDs de taqueros]
            0 -> Adobaba
            1 -> Asada y Suadero (1)
            2 -> Asada y Suadero (2)
            3 -> Tripa y cabeza 
            4 -> El de las quesadillas
        """
        cocina.personal.append(PersonalTaqueria("Omar"))
        cocina.personal[0].chalanAsignado = ChalanTaquero("Julio")
        cocina.personal[0].start()
        cocina.personal[0].ID = 0
        cocina.personal[0].chalanAsignado.start()


class CocinaQuesadillero():
    pass


def open_taqueria():
    # Solo poner estas ordenes mientras hacemos pruebas
    ordersToTest = 4
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
        #x = input()
