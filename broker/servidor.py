import zmq

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.connect("tcp://broker:5556")

usuarios = list()

while True:
    msg = socket.recv_string()
    funcao, resto = msg.split()
