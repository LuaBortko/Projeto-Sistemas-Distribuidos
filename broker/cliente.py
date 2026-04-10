import zmq
from time import sleep
from datetime import datetime
import zoneinfo
import msgpack

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://broker:5555")
fuso = zoneinfo.ZoneInfo("America/Sao_Paulo")


def mandar(func, user, channel):
    tempo = datetime.now(tz=fuso).strftime("%H:%M")
    data = {"user": user, "func": func, "channel": channel, "time": tempo}
    print(f"Mensagem do usuario em {tempo}. Mensagem: {data}", flush=True)
    packet = msgpack.packb(data)
    socket.send(packet)  # Enviando a mensagem para o servidor


while True:
    mandar("login", "py1", "")
    recebido = msgpack.unpackb(socket.recv())  # Mensagem recebida do servidor
    print(f"Resposta do servidor: {recebido}", flush=True)
    sleep(2)
    mandar("entrar", "py1", "CanalPython")
    recebido = msgpack.unpackb(socket.recv())  # Mensagem recebida do servidor
    print(f"Resposta do servidor: {recebido}", flush=True)
    sleep(2)
    mandar("listar", "py2", "")
    recebido = msgpack.unpackb(socket.recv())  # Mensagem recebida do servidor
    print(f"Resposta do servidor: {recebido}", flush=True)
    sleep(2)
    mandar("listar", "py1", "")
    recebido = msgpack.unpackb(socket.recv())  # Mensagem recebida do servidor
    print(f"Resposta do servidor: {recebido}", flush=True)
    sleep(4)
