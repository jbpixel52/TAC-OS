#%%
from datetime import datetime
import random
import boto3
import json
import time
sqs = boto3.client('sqs')
who = 'TAC-OS'
queue_url ="https://sqs.us-east-1.amazonaws.com/292274580527/sqs_cc106_team_4"
def get_number_messages():
    queue_attr = sqs.get_queue_attributes(
    QueueUrl = queue_url,
    AttributeNames = ['ApproximateNumberOfMessages']
    )
    return int(queue_attr['Attributes']['ApproximateNumberOfMessages']) 

def read_message():
    response = sqs.receive_message(QueueUrl =queue_url)
    if 'Messages' in response:
        message = response['Messages']
        orden = json.loads(message[0]['Body'])
        print(f"Atendiendo orden {orden['request_id']} Leyendo mensaje del queue. Tiempo pendiente  {orden['tiempo_pendiente']}")
        return message[0],orden

def delete_message(message,orden,complete):
    sqs.delete_message(
    QueueUrl = queue_url,
    ReceiptHandle = message["ReceiptHandle"] )
    if complete:
        orden ["end_datetime"] = str(datetime.now().timestamp())
        print(f"Orden {orden['request_id']} Terminada. Mensaje borrado del queue.")
        print(orden)
    else:
        print(f"Orden {orden['request_id']} Pendiente. Regresando mensaje del queue. Tiempo Pendiente {orden['tiempo_pendiente']}")


def write_message(mensaje,orden):
    delete_message(mensaje,orden,False)
    response=sqs.send_message(
        QueueUrl = queue_url,
        MessageBody=(json.dumps(orden))
    )
    
def round_robin():
    while True:
        print(f"Ordenes pendientes:{get_number_messages()}")
        time.sleep(2)
        mensaje, orden = read_message()
        orden['tiempo_pendiente']= orden['tiempo_pendiente']-2
        orden["process"].append({"who":who,"new_tiempo_pendiente":orden["tiempo_pendiente"]})
        if orden["tiempo_pendiente"] <= 0:
            delete_message(mensaje,orden,True)
        else:
            write_message(mensaje, orden)
        

def init():
    total=9
    print(f'Agregando {total} ordenes a SQS')
    for index in range(total):
        orden={
            'start_datetime':str(datetime.now().timestamp()),
            'end_time':"",
            'request_id':index,
            "tiempo_pendiente":random.randrange(25),
            "process":[]
        }
        response = sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=(json.dumps(orden))
        )
        print(response)
            
    round_robin()
        
init()
# %%
