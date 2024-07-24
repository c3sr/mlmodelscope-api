import pika
import os
import json
import uuid
import time

MQ_HOST = os.environ.get('MQ_HOST', 'localhost')
MQ_PORT = int(os.environ.get('MQ_PORT', '5672'))
MQ_USER = os.environ.get('MQ_USER', 'user')
MQ_PASS = os.environ.get('MQ_PASS', 'password')



def connect():
    parameters = pika.ConnectionParameters(
        MQ_HOST,
        MQ_PORT,
        '/',
        pika.PlainCredentials(MQ_USER, MQ_PASS),
        heartbeat=60,
        blocked_connection_timeout=300
    )
    return pika.BlockingConnection(parameters)

def makePredictMessage(architecture, batch_size, desired_result_modality, gpu, inputs,has_multi_input,context,config,model_name, trace_level, warmups, tracer_address):
    return {
        "BatchSize": batch_size,
        "DesiredResultModality": desired_result_modality,
        "InputFiles": inputs,
        "HasMultiInput": has_multi_input,
        "Context": context,
        "Configuration": config,
        "ModelName": model_name,
        "NumWarmup": warmups,
        "TraceLevel": trace_level,
        "TracerAddress": tracer_address,
        "UseGpu": gpu
    }

def sendPredictMessage(message, queue_name, correlation_id):
    while True:
        try:
            connection = connect()
            channel = connection.channel()
            message_bytes = json.dumps(message).encode('utf-8')
            channel.basic_publish(
                exchange='',
                routing_key=queue_name,
                body=message_bytes,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # make message persistent
                    correlation_id=correlation_id
                )
            )
            # print(" [x] Sent 'Predict Message'")
            channel.close()
            connection.close()
            break
        except (pika.exceptions.StreamLostError, pika.exceptions.AMQPConnectionError) as e:
            print(f"Connection lost: {e}. Reconnecting in 5 seconds...")
            time.sleep(5)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            break

