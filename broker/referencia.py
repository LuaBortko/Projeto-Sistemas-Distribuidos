import zmq
import time
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
    mortos = [s for s in servidores if agora - s["last_time"] > tempo]
    for servidor in mortos:
        print(f"Removendo servidor {servidor['name']}", flush=True)
        servidores.remove(servidor)
    if mortos:
        salvar_servidores()  

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.connect("tcp://broker2:5550")
intervalo = 30  # segundos sem heartbeat para remover servidor

servidores = list()
carregar_servidores()
print("Servidores ativos salvos:", servidores)

poller = zmq.Poller()
poller.register(socket, zmq.POLLIN)

while True:
    limpar_servidores(intervalo)
    eventos = dict(poller.poll(5000))

    if socket not in eventos:
        continue

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
            servidores.append({"name": name, "rank": rank, "last_time": time.time()})
            salvar_servidores()

        socket.send(msgpack.packb({"rank": rank}))
        print(f"Solicitação de rank do servidor {name} e rank {rank}", flush=True)

    elif funcao == "listar":
        socket.send(msgpack.packb({"lista": servidores}))
        print("Solicitação da lista de servidores", flush=True)

    elif funcao == "heartbeat":
        achei = False
        for servidor in servidores:
            if servidor["name"] == name:
                servidor["last_time"] = time.time()
                achei = True
                break
        if not achei:
            socket.send(msgpack.packb({"status": "err"}))
            print(f"Servidor não encontrado: {name}", flush=True)
        else:
            socket.send(msgpack.packb({"status": "ok"}))
            print(f"Heartbeat de {name}", flush=True)
