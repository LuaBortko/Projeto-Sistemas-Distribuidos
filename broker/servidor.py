import zmq
from time import sleep
from datetime import datetime
import zoneinfo
import msgpack
import pickle
import os

ARQUIVO = "dados.pkl"
ARQUIVO_MSG = "msgs.pkl"


def salvar_dados():
    with open(ARQUIVO, "wb") as f:
        pickle.dump({
            "usuarios": usuarios,
            "canais": canais
        }, f)


def carregar_dados():
    global usuarios, usuariosLogados, canais

    if os.path.exists(ARQUIVO):
        with open(ARQUIVO, "rb") as f:
            dados = pickle.load(f)
            usuarios = dados.get("usuarios", [])
            canais = dados.get("canais", [])


def carregar_mensagens():
    global mensagens

    if os.path.exists(ARQUIVO_MSG):
        with open(ARQUIVO_MSG, "rb") as f:
            mensagens = pickle.load(f)


def salvar_mensagens():
    with open(ARQUIVO_MSG, "wb") as f:
        pickle.dump(mensagens, f)


context = zmq.Context()
socket = context.socket(zmq.REP)
socket.connect("tcp://broker:5556")
fuso = zoneinfo.ZoneInfo("America/Sao_Paulo")
pub = context.socket(zmq.PUB)
pub.connect("tcp://pubsub:5557")

usuarios = list()
usuariosLogados = list()
canais = list()
mensagens = []
carregar_dados()
carregar_mensagens()
print("Mensagens salvas:", len(mensagens))
print("Usuarios salvos: ", usuarios)
print("Canais salvos: ", canais)

while True:
    data = socket.recv()
    msg = msgpack.unpackb(data)
    funcao = msg["func"]
    user = msg["user"]
    canal = msg["channel"]
    tempo = msg["time"]
    mensagem = msg["msg"]

    if funcao == "login":
        if user in usuariosLogados:
            data = {"situ": "erro-login"}
            packet = msgpack.packb(data)
            socket.send(packet)
            print(
                f"Erro ao entrar no servidor as {tempo}, usuario ja logado", flush=True)
        else:
            if user not in usuarios:
                usuarios.append(user)
                salvar_dados()
            usuariosLogados.append(user)
            data = {"situ": "success"}
            packet = msgpack.packb(data)
            socket.send(packet)
            print(
                f"O usuario {user} entrou no servidor com sucesso as {tempo}", flush=True)

    elif funcao == "entrar":
        if user not in usuariosLogados:
            data = {"situ": "erro-semLogin"}
            packet = msgpack.packb(data)
            socket.send(packet)
            print(
                f"O usuario {user} não esta logado, tentativa de acesso as {tempo}", flush=True)
        else:
            if canal not in canais:
                canais.append(canal)
                salvar_dados()
                data = {"situ": "success"}
                packet = msgpack.packb(data)
                socket.send(packet)
                print(
                    f"Canal não encontrado, criado novo canal com o nome {canal} as {tempo}", flush=True)
            else:
                data = {"situ": "success"}
                packet = msgpack.packb(data)
                socket.send(packet)
                print(f"Entrou no canal {canal} com sucesso! as {tempo}")

    elif funcao == "listar":
        if user not in usuariosLogados:
            data = {"situ": "erro-semLogin"}
            packet = msgpack.packb(data)
            socket.send(packet)
            print(
                f"O usuario {user} não esta logado, tentativa de acesso as {tempo}", flush=True)
        else:
            # print(canais)
            data = {"situ": "success", "canais": canais}
            socket.send(msgpack.packb(data))

    elif funcao == "publicar":
        if user not in usuariosLogados:
            data = {"situ": "erro-semLogin"}
        elif canal not in canais:
            data = {"situ": "erro-canal"}

        else:
            pub_msg = {
                "user": user,
                "channel": canal,
                "msg": mensagem,
                "time": tempo
            }
            pub.send_multipart([
                canal.encode(),
                msgpack.packb(pub_msg)
            ])
            mensagens.append(pub_msg)
            salvar_mensagens()
            print(f"[PUB] {user} -> {canal}: {mensagem} ({tempo})", flush=True)
            data = {"situ": "success"}
            sleep(1)
        socket.send(msgpack.packb(data))
    else:
        data = {"situ": "erro-comando"}
        packet = msgpack.packb(data)
        socket.send(packet)
        print(f"Comando não reconhecido as {tempo}", flush=True)
