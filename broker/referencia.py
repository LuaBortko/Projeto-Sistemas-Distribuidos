import zmq
from time import sleep
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


context = zmq.Context()
socket = context.socket(zmq.REP)
socket.connect("tcp://broker:5556")
fuso = zoneinfo.ZoneInfo("America/Sao_Paulo")

servidores = list()

carregar_servidores()
print("Servidores ativos salvos:", len(servidores))

while True:
    pass
