from main_scheduler import CocinaTaqueros, ChalanTaquero, PersonalTaqueria



def main():
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
        x = input()
