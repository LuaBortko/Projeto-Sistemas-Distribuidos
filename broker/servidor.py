import zmq
from time import sleep
from datetime import datetime
import zoneinfo
import msgpack

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.connect("tcp://broker:5556")
fuso = zoneinfo.ZoneInfo("America/Sao_Paulo")

usuarios = list()
usuariosLogados = list()
canais = list()

while True:
    data = socket.recv()
    msg = msgpack.unpackb(data)
    funcao = msg["func"]
    user = msg["user"]
    canal = msg["channel"]
    tempo = msg["time"]

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
            data = {"situ": "success"}
            packet = msgpack.packb(data)
            socket.send(packet)
            print(canais)

    else:
        data = {"situ": "erro-comando"}
        packet = msgpack.packb(data)
        socket.send(packet)
        print(f"Comando não reconhecido as {tempo}", flush=True)
