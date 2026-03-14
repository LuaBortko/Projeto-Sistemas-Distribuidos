import zmq
from time import sleep
from datetime import datetime
import zoneinfo

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://broker:5555")
fuso = zoneinfo.ZoneInfo("America/Sao_Paulo")


def mandar(msg):
    tempo = datetime.now(tz=fuso).strftime("%H:%M")
    print(f"Mensagem do usuario em {tempo}. Mensagem: {msg}", flush=True)
    socket.send_string(msg)  # Enviando a mensagem para o servidor


while True:
    mandar("login usuario1 -")
    recebido = socket.recv()  # Mensagem recebida do servidor
    print(f"Resposta do servidor: {recebido}", flush=True)
    # if recebido == "success":
    sleep(2)
    mandar("entrar usuario1 teste1")
    recebido = socket.recv()
    print(f"Resposta do servidor: {recebido}", flush=True)
    sleep(2)
    mandar("listar usuario2 -")
    recebido = socket.recv()
    print(f"Resposta do servidor: {recebido}", flush=True)
    sleep(2)
    mandar("listar usuario1 -")
    recebido = socket.recv()
    print(f"Resposta do servidor: {recebido}", flush=True)
    sleep(4)
