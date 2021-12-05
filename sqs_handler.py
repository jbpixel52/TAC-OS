# %%
from datetime import datetime
import random
import boto3
import json
import time
sqs = boto3.client('sqs')
WHO = 'TAC-OS'
QUEUE_URL = "https://sqs.us-east-1.amazonaws.com/292274580527/sqs_cc106_team_4"


def create_queue():
    response = sqs.create_queue(
        QueueName="my-new-queue",
        Attributes={
            "DelaySeconds": "0",
            "VisibilityTimeout": "60",  # 60 seconds
        }
    )
    print(response)


def get_queue_url(_name):
    response = sqs.get_queue_url(
        QueueName=_name,
    )
    return response["QueueUrl"]


def get_number_messages():
    queue_attr = sqs.get_queue_attributes(
        QueueUrl=QUEUE_URL,
        AttributeNames=['ApproximateNumberOfMessages']
    )
    return int(queue_attr['Attributes']['ApproximateNumberOfMessages'])


def read_message():
    response = sqs.receive_message(QueueUrl=QUEUE_URL)
    if 'Messages' in response:
        message = response['Messages']
        orden = json.loads(message[0]['Body'])
        print(
            f"Atendiendo orden {orden['request_id']} Leyendo mensaje del queue")
        return [message,orden]


def delete_message(message, orden, complete):

    if complete:
        orden["end_datetime"] = str(datetime.now().timestamp())
        print(
            f"Orden {orden['request_id']} Terminada. Mensaje sera borrado del queue.")
        sqs.delete_message(
        QueueUrl=QUEUE_URL,
        ReceiptHandle=message["ReceiptHandle"])
        print(orden)
        return print('MENSAJE BORRADO')
    else:
        print(
            f"Orden {orden['request_id']} Pendiente. Regresando mensaje del queue")


def send_message(outputqueue,mensaje, orden):
    delete_message(mensaje, orden, True)
    response = sqs.send_message(
        QueueUrl=outputqueue,
        MessageBody=(json.dumps(orden))
    )
    print(response)


def round_robin():
    while get_number_messages() > 0:
        print(f"Ordenes pendientes:{get_number_messages()}")
        # time.sleep(2)
        mensaje, orden = read_message()
        orden['tiempo_pendiente'] = 0  # SIMULAR QUE SE ATENDIO con -=
        orden["process"].append(
            {"who": WHO, "new_tiempo_pendiente": orden["tiempo_pendiente"]})
        if orden["tiempo_pendiente"] <= 0:
            delete_message(mensaje, orden, True)
        else:
            send_message(mensaje, orden)


def purge_queue():
    # SOLO SE PUEDE HACER CADA 60 SEGUNDOS
    response = sqs.purge_queue(
        QueueUrl=QUEUE_URL,
    )
    print(f'Purged queue: {QUEUE_URL}')
    print(response)


def init():
    total = 6
    print(f'Agregando {total} ordenes a SQS')
    for index in range(total):
        orden = {
        "datetime": datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
        "request_id": index,
        "status": "open",
        "orden": [
            {
                "part_id": "2-0",
                "type": "quesadilla",
                "meat": "suadero",
                "status": "open",
                "quantity": 69,
                "ingredients": []
            },
            {
                "part_id": "2-1",
                "type": "taco",
                "meat": "suadero",
                "status": "open",
                "quantity": 35,
                "ingredients": [
                    "cebolla",
                    "salsa"
                ]
            },
            {
                "part_id": "2-2",
                "type": "taco",
                "meat": "asada",
                "status": "open",
                "quantity": 69,
                "ingredients": [
                    "cebolla",
                    "cilantro"
                ]
            },
            {
                "part_id": "2-3",
                "type": "taco",
                "meat": "tripa",
                "status": "open",
                "quantity": 17,
                "ingredients": [
                    "salsa",
                    "cilantro",
                    "guacamole"
                ]
            },
            {
                "part_id": "2-4",
                "type": "taco",
                "meat": "cabeza",
                "status": "open",
                "quantity": 91,
                "ingredients": [
                    "guacamole",
                    "cebolla",
                    "cilantro"
                ]
            }
        ]
    }
    response = sqs.send_message(
        QueueUrl=QUEUE_URL,
        MessageBody=(json.dumps(orden))
    )
    print(response)


init()
read_message()

# %%
