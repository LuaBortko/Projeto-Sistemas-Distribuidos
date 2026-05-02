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
rank = -1
msg = {
    "func": "rank",
    "name": nome
}

req.send(msgpack.packb(msg))
resposta = msgpack.unpackb(req.recv())
print(f"Servidor {nome} recebeu o rank {resposta['rank']}")
rank = resposta["rank"]
msg2 = {
    "func": "listar",
    "name": nome
}
req.send(msgpack.packb(msg2))
resposta = msgpack.unpackb(req.recv())
print("Servidores ativos:", resposta["lista"])

contador_heartbeat = 0
contador_relogio = 0

# --- Eleição ---
coordenador = ""
# Começa no passado para que o timeout dispare se nenhum coordenador aparecer
ultimo_heartbeat_coord = 0.0
intervalo_heartbeat = 3   # segundos entre heartbeats do coordenador
timeout_coordenador = 10  # tempo sem heartbeat antes de nova eleição

eleicao = False
existe_maior = False      # alguém com rank maior respondeu ao nosso pedido?
timeout_eleicao = 0.0

startup_time = datetime.now().timestamp()
tempo_descoberta = 8 + rank * 2  # rank 0 espera 8s, rank 1 espera 10s, etc.

#Socket sub para saber se houve eleição
sub_servers = context.socket(zmq.SUB)
sub_servers.connect("tcp://proxy:5558")   # porta do XPUB (consumidor)
sub_servers.setsockopt_string(zmq.SUBSCRIBE, "servers")

#Poller pra não travar com o cliente e não conseguir receber mensagens do canal servers
poller = zmq.Poller()
poller.register(socket, zmq.POLLIN)
poller.register(sub_servers, zmq.POLLIN)


def iniciar_eleicao():
    print("[ELEICAO] Iniciando eleição")
    global eleicao, existe_maior, timeout_eleicao
    eleicao = True
    existe_maior = False
    timeout_eleicao = datetime.now().timestamp()

    msg = {
        "tipo": "Eleicao",
        "autor": nome,
        "rank": rank
    }
    pub.send_multipart([b"servers", msgpack.packb(msg)])


while True:

    eventos = dict(poller.poll(1000))

    if socket in eventos:
        data = socket.recv()
        contador_heartbeat += 1
        msg = msgpack.unpackb(data)

        funcao = msg["func"]
        user = msg["user"]
        canal = msg["channel"]
        tempo = msg["time"]
        mensagem = msg["msg"]
        cont = msg["contador"]

        if contador_heartbeat >= 10:
            heartbeat = {
                "func": "heartbeat",
                "name": nome
            }
            req.send(msgpack.packb(heartbeat))
            resposta = msgpack.unpackb(req.recv())
            print("[HEARTBEAT] enviado")
            print("Resposta da Referencia:", resposta["status"])
            contador_heartbeat = 0

        if cont > contador:
            contador = cont + 1

        if funcao == "login":
            if user in usuariosLogados:
                contador += 1
                data = {"situ": "erro-login", "contador": contador}
                packet = msgpack.packb(data)
                socket.send(packet)
                print(f"Erro ao entrar no servidor as {tempo}, usuario ja logado", flush=True)
            else:
                if user not in usuarios:
                    usuarios.append(user)
                    salvar_dados()
                usuariosLogados.append(user)
                contador += 1
                data = {"situ": "success", "contador": contador}
                packet = msgpack.packb(data)
                socket.send(packet)
                print(f"O usuario {user} entrou no servidor com sucesso as {tempo}", flush=True)

        elif funcao == "entrar":
            if user not in usuariosLogados:
                contador += 1
                data = {"situ": "erro-semLogin", "contador": contador}
                packet = msgpack.packb(data)
                socket.send(packet)
                print(f"O usuario {user} não esta logado, tentativa de acesso as {tempo}", flush=True)
            else:
                if canal not in canais:
                    canais.append(canal)
                    salvar_dados()
                    contador += 1
                    data = {"situ": "success", "contador": contador}
                    packet = msgpack.packb(data)
                    socket.send(packet)
                    print(f"Canal não encontrado, criado novo canal com o nome {canal} as {tempo}", flush=True)
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
                print(f"O usuario {user} não esta logado, tentativa de acesso as {tempo}", flush=True)
            else:
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
                print(f"[PUB] {user} -> {canal}: {mensagem} ({tempo}) Relogio Logico: {contador}", flush=True)
                data = {"situ": "success", "contador": contador}
                sleep(1)
            socket.send(msgpack.packb(data))
        else:
            contador += 1
            data = {"situ": "erro-comando", "contador": contador}
            packet = msgpack.packb(data)
            socket.send(packet)
            print(f"Comando não reconhecido as {tempo}", flush=True)

    if sub_servers in eventos:
        topico, dados = sub_servers.recv_multipart()
        msg = msgpack.unpackb(dados)
        tipo = msg["tipo"]
        autor = msg.get("autor", "")

        if autor == nome and tipo in ("Eleicao", "ok"):
            pass

        elif tipo == "Eleicao":
            rank_eleicao = msg["rank"]
            print(f"[ELEICAO] Recebi pedido de {autor} (rank {rank_eleicao}), meu rank: {rank}")

            if rank > rank_eleicao:
                resposta_ok = {
                    "tipo": "ok",
                    "autor": nome,
                    # destinatario é quem pediu: só ele deve setar existe_maior
                    "para": autor
                }
                pub.send_multipart([b"servers", msgpack.packb(resposta_ok)])
                print(f"[ELEICAO] Enviei OK para {autor}")

                # Propago a eleição se ainda não estou em uma
                if not eleicao:
                    iniciar_eleicao()

        elif tipo == "ok":
            if msg.get("para") == nome:
                print(f"[ELEICAO] Recebi OK de {autor} — existe alguém maior que eu")
                existe_maior = True

        elif tipo == "Coordenador":
            novo_coord = msg["name"]
            rank_coord = msg["rank"]
            if rank_coord > rank or novo_coord == nome:
                coordenador = novo_coord
                eleicao = False
                existe_maior = False
                ultimo_heartbeat_coord = datetime.now().timestamp()
                print(f"[COORDENADOR ACEITO] {coordenador} (rank {rank_coord})")
            else:
                print(f"[IGNORADO] Coordenador {novo_coord} tem rank {rank_coord} <= meu rank {rank}")

        elif tipo == "heartbeat":
            if msg["name"] == coordenador:
                ultimo_heartbeat_coord = datetime.now().timestamp()

    agora = datetime.now().timestamp()

    if eleicao and not existe_maior:
        if agora - timeout_eleicao > 3:
            print("[ELEICAO] Timeout — sou o novo coordenador!")
            coordenador = nome
            eleicao = False
            existe_maior = False
            ultimo_heartbeat_coord = agora

            msg = {
                "tipo": "Coordenador",
                "autor": nome,   # adicionado para consistência
                "name": nome,
                "rank": rank
            }
            pub.send_multipart([b"servers", msgpack.packb(msg)])

    # Coordenador envia heartbeat periodicamente
    if coordenador == nome:
        if agora - ultimo_heartbeat_coord > intervalo_heartbeat:
            msg = {
                "tipo": "heartbeat",
                "autor": nome,
                "name": nome
            }
            pub.send_multipart([b"servers", msgpack.packb(msg)])
            print("[HEARTBEAT] Coordenador vivo")
            ultimo_heartbeat_coord = agora

    # Inicia eleição no startup se não há coordenador
    if coordenador == "" and not eleicao and agora - startup_time > tempo_descoberta:
        print("[STARTUP] Nenhum coordenador encontrado, iniciando eleição")
        iniciar_eleicao()

    # Não-coordenadores: disparam eleição se coordenador sumir
    elif coordenador != nome and coordenador != "" and not eleicao:
        if agora - ultimo_heartbeat_coord > timeout_coordenador:
            print(f"[FALHA] Coordenador {coordenador} não responde!")
            coordenador = ""
            iniciar_eleicao()
