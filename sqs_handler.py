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
            f"Atendiendo orden {orden['request_id']} Leyendo mensaje del queue. Tiempo pendiente  {orden['tiempo_pendiente']}")
        return message[0], orden


def delete_message(message, orden, complete):
    sqs.delete_message(
        QueueUrl=QUEUE_URL,
        ReceiptHandle=message["ReceiptHandle"])
    if complete:
        orden["end_datetime"] = str(datetime.now().timestamp())
        print(
            f"Orden {orden['request_id']} Terminada. Mensaje borrado del queue.")
        print(orden)
    else:
        print(
            f"Orden {orden['request_id']} Pendiente. Regresando mensaje del queue. Tiempo Pendiente {orden['tiempo_pendiente']}")


def send_message(mensaje, orden):
    delete_message(mensaje, orden, False)
    response = sqs.send_message(
        QueueUrl=QUEUE_URL,
        MessageBody=(json.dumps(orden))
    )
    print(response)

def round_robin():
    while get_number_messages() > 0:
        print(f"Ordenes pendientes:{get_number_messages()}")
        # time.sleep(2)
        mensaje, orden = read_message()
        orden['tiempo_pendiente'] = 0 #SIMULAR QUE SE ATENDIO con -=
        orden["process"].append(
            {"who": WHO, "new_tiempo_pendiente": orden["tiempo_pendiente"]})
        if orden["tiempo_pendiente"] <= 0:
            delete_message(mensaje, orden, True)
        else:
            send_message(mensaje, orden)


def purge_queue():
    #SOLO SE PUEDE HACER CADA 60 SEGUNDOS
    response = sqs.purge_queue(
        QueueUrl=QUEUE_URL,
    )
    print(f'Purged queue: {QUEUE_URL}')
    print(response)


def init():
    total = 3
    print(f'Agregando {total} ordenes a SQS')
    for index in range(total):
        orden = {
            'start_datetime': str(datetime.now().timestamp()),
            'end_time': "",
            'request_id': index,
            "tiempo_pendiente": random.randrange(25),
            "process": []
        }
        response = sqs.send_message(
            QueueUrl=QUEUE_URL,
            MessageBody=(json.dumps(orden))
        )
        print(response)

    round_robin()


init()
#purge_queue()
# %%
