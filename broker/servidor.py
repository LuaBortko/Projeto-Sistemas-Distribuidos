import zmq
from time import sleep
from datetime import datetime
import zoneinfo
import msgpack
import pickle
import os
import socket as pysocket

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
pub.connect("tcp://proxy:5557")

#Adição da comunicação com a referencia
req = context.socket(zmq.REQ)
req.connect("tcp://broker2:5559")

usuarios = list()
usuariosLogados = list()
canais = list()
mensagens = []
carregar_dados()
carregar_mensagens()
print("Mensagens salvas:", len(mensagens))
print("Usuarios salvos: ", usuarios)
print("Canais salvos: ", canais)
contador = 0

#Conversa inicial com a referencia
nome = pysocket.gethostname()
msg = {
    "func": "rank",
    "name": nome
}

req.send(msgpack.packb(msg))
resposta = msgpack.unpackb(req.recv())
print("Resposta do rank recebida: ", resposta)

msg2 = {
    "func": "listar",
    "name": nome
}
req.send(msgpack.packb(msg2))
resposta = msgpack.unpackb(req.recv())
print("Servidores ativos:", resposta["lista"])

contador_heartbeat = 0;
while True:
    data = socket.recv()
    contador_heartbeat += 1

    if contador_heartbeat >= 10:
        heartbeat = {
            "func": "heartbeat",
            "name": nome
        }
        req.send(msgpack.packb(heartbeat))
        resposta = msgpack.unpackb(req.recv())  # só um recv
        print("[HEARTBEAT] enviado")
        print("Resposta da Referencia:", resposta["status"])
        contador_heartbeat = 0

    msg = msgpack.unpackb(data)
    funcao = msg["func"]
    user = msg["user"]
    canal = msg["channel"]
    tempo = msg["time"]
    mensagem = msg["msg"]
    cont = msg["contador"]
    if cont > contador:
        contador = cont+1

    if funcao == "login":
        if user in usuariosLogados:
            contador += 1
            data = {"situ": "erro-login", "contador": contador}
            packet = msgpack.packb(data)
            socket.send(packet)
            print(
                f"Erro ao entrar no servidor as {tempo}, usuario ja logado", flush=True)
        else:
            if user not in usuarios:
                usuarios.append(user)
                salvar_dados()
            usuariosLogados.append(user)
            contador += 1
            data = {"situ": "success", "contador": contador}
            packet = msgpack.packb(data)
            socket.send(packet)
            print(
                f"O usuario {user} entrou no servidor com sucesso as {tempo}", flush=True)

    elif funcao == "entrar":
        if user not in usuariosLogados:
            contador += 1
            data = {"situ": "erro-semLogin", "contador": contador}
            packet = msgpack.packb(data)
            socket.send(packet)
            print(
                f"O usuario {user} não esta logado, tentativa de acesso as {tempo}", flush=True)
        else:
            if canal not in canais:
                canais.append(canal)
                salvar_dados()
                contador += 1
                data = {"situ": "success", "contador": contador}
                packet = msgpack.packb(data)
                socket.send(packet)
                print(
                    f"Canal não encontrado, criado novo canal com o nome {canal} as {tempo}", flush=True)
            else:
                contador += 1
                data = {"situ": "success", "contador": contador}
                packet = msgpack.packb(data)
                socket.send(packet)
                print(f"Entrou no canal {canal} com sucesso! as {tempo}")

    elif funcao == "listar":
        if user not in usuariosLogados:
            contador += 1
            data = {"situ": "erro-semLogin", "contador": contador}
            packet = msgpack.packb(data)
            socket.send(packet)
            print(
                f"O usuario {user} não esta logado, tentativa de acesso as {tempo}", flush=True)
        else:
            # print(canais)
            contador += 1
            data = {"situ": "success", "canais": canais, "contador": contador}
            socket.send(msgpack.packb(data))

    elif funcao == "publicar":
        contador += 1
        if user not in usuariosLogados:
            data = {"situ": "erro-semLogin", "contador": contador}
        elif canal not in canais:
            data = {"situ": "erro-canal", "contador": contador}

        else:
            pub_msg = {
                "user": user,
                "channel": canal,
                "msg": mensagem,
                "time": tempo,
                "contador": contador
            }
            pub.send_multipart([
                canal.encode(),
                msgpack.packb(pub_msg)
            ])
            mensagens.append(pub_msg)
            salvar_mensagens()
            print(
                f"[PUB] {user} -> {canal}: {mensagem} ({tempo}) Relogio Logico: {contador}", flush=True)
            data = {"situ": "success", "contador": contador}
            sleep(1)
        socket.send(msgpack.packb(data))
    else:
        contador += 1
        data = {"situ": "erro-comando", "contador": contador}
        packet = msgpack.packb(data)
        socket.send(packet)
        print(f"Comando não reconhecido as {tempo}", flush=True)
