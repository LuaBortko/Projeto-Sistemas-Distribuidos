import zmq
from time import sleep
from datetime import datetime
import zoneinfo

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.connect("tcp://broker:5556")
fuso = zoneinfo.ZoneInfo("America/Sao_Paulo")

usuarios = list()
usuariosLogados = list()
canais = list()

while True:
    msg = socket.recv_string()
    funcao, user, canal = msg.split()
    tempo = datetime.now(tz=fuso).strftime("%H:%M")
    if funcao == "login":
        if user in usuariosLogados:
            socket.send_string("err2")
            print(
                f"Erro ao entrar no servidor as {tempo}, nome ja existente", flush=True)
        else:
            if user not in usuarios:
                usuarios.append(user)
            usuariosLogados.append(user)
            socket.send_string("success")
            print(
                f"O usuario {user} entrou no servidor com sucesso as {tempo}", flush=True)
    elif funcao == "entrar":
        if user not in usuariosLogados:
            socket.send_string("err3")
            print(
                f"O usuario {user} não esta logado, tentativa de acesso as {tempo}", flush=True)
        else:
            if canal not in canais:
                canais.append(canal)
                socket.send_string("success")
                print(
                    f"Canal não encontrado, criado novo canal com o nome {canal} as {tempo}", flush=True)
            else:
                socket.send_string("success")
                print(f"Entrou no canal {canal} com sucesso! as {tempo}")
    elif funcao == "listar":
        if user not in usuariosLogados:
            socket.send_string("err3")
            print(
                f"O usuario {user} não esta logado, tentativa de acesso as {tempo}", flush=True)
        else:
            socket.send_string("success")
            print(canais)

    else:
        socket.send_string("err1")
        print(f"Comando não reconhecido as {tempo}", flush=True)
