import zmq
import time
from datetime import datetime
import zoneinfo
import msgpack
import pickle
import os

ARQUIVO = "servidores.pkl"

def carregar_servidores():
    global servidores

    if os.path.exists(ARQUIVO):
        with open(ARQUIVO, "rb") as f:
            servidores = pickle.load(f)


def salvar_servidores():
    with open(ARQUIVO, "wb") as f:
        pickle.dump(servidores, f)

def limpar_servidores(tempo):
    agora = time.time()
    mortos = []

    for servidor in servidores:
        if agora - servidor["last_time"] > tempo:
            mortos.append(servidor)

    for servidor in mortos:
        print(f"Removendo servidor {servidor['name']}")
        servidores.remove(servidor)

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.connect("tcp://broker2:5550")
fuso = zoneinfo.ZoneInfo("America/Sao_Paulo")
intervalo = 30

servidores = list()

carregar_servidores()
print("Servidores ativos salvos:", servidores)

while True:
    limpar_servidores(intervalo)

    data = socket.recv()
    msg = msgpack.unpackb(data)
    funcao = msg["func"]
    name = msg["name"]
    if funcao == "rank":
        rank = -1
        for servidor in servidores:
            if servidor["name"] == name:
                rank = servidor["rank"]
                break
        if rank == -1:
            rank = len(servidores)
            servidores.append({"name":name,"rank":rank,"last_time":time.time()})
            salvar_servidores()
            
        data = {"rank": rank}
        packet = msgpack.packb(data)
        socket.send(packet)
        print(f"Solicitação de rank do servidor {name} e rank {rank}", flush=True)

    elif funcao == "listar":
        data = {"lista": servidores}
        packet = msgpack.packb(data)
        socket.send(packet)
        print(f"Solicitação da lista de servidores",flush=True)
    
    elif funcao == "heartbeat":
        achei = -1
        for servidor in servidores:
            if servidor["name"] == name:
                servidor["last_time"] = time.time()
                achei = 1
                break
        if achei == -1:
            socket.send(msgpack.packb({"status": "err"}))
            print(f"Servidor não encontrado",flush=True)

        else:
            socket.send(msgpack.packb({"status": "ok"}))
