import multiprocessing
import threading
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
        self.ordenes = []

        pass

    def main(self):
        # Formato de prueba
        #  Orden  = (tiempollegada,duracionOrden)
        print("Taquero {} en linea".format(self.name))

        self.OrderRecieverThread.start()
        self.CookerThread.start()
        pass

    def recieveClientOrders(self):
        while(True):
            LaHora = getTime()
            print("{}:{}".format(LaHora, self.ordenes))
            f = open("demofile2.txt", "a")
            f.write("{}:{}\n".format(LaHora, self.ordenes))
            try:
                newOrder = self.queue.get_nowait()
                self.ordenes.append(newOrder)
                self.Rescheduling = True
                self.ordenes.sort()
                self.Rescheduling = False
            except:
                #print("Error #1")
                pass  
            time.sleep(self.ordersPerSecondDelta)
    
    def cook(self):
        while(True):
            if(len(self.ordenes)>0 and (not self.Rescheduling)):
                if(self.ordenes[0] > 0.5):
                    self.ordenes[0] -= 0.5
                else:
                    self.ordenes.pop(0)
                pass
            else:
                if(self.Rescheduling):
                    print(self.Rescheduling)
                    print("NoPuedoEntrar:(")
                else:
                    print("Ordenes es 0")
            time.sleep(self.cookUnitDelta)
            

class CocinaTaqueros(multiprocessing.Process):
    def __init__(self,nombre):
        #SuperConsteructor
        super(CocinaTaqueros, self).__init__(target = self.main, name = nombre)
        self.personal = []
        pass

    def main(self):
        print("Cocina encendida")
        pass

## class CocinaQuesadillero()



if __name__ == "__main__":
    print("Scheduler test 1")
    Cocina = CocinaTaqueros("Taqueros")
    Cocina.start()
    Cocina.personal.append(PersonalTaqueria("Omar"))
    Cocina.personal[0].start()

    while(True):
        print("Escriba la cantidad de unidades que tiene este indice: \n")
        orden = int(input())
        Cocina.personal[0].queue.put(orden)
    
    #x = 5
    #print(getTime())
