import zmq
from time import sleep

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://broker:5555")


msg = "login usuario1"
print(f"Requerimento de Login do usuario: {msg}", flush=True)
socket.send_string(msg)  # Enviando a mensagem para o servidor
recebido = socket.recv()  # Mensagem recebida do servidor
print(f"Resposta do servidor:{recebido}", flush=True)
sleep(1)
