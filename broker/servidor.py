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

PORTA_BERKELEY = 6000  # porta direta entre servidores


def salvar_dados():
    with open(ARQUIVO, "wb") as f:
        pickle.dump({"usuarios": usuarios, "canais": canais}, f)


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

socket_clientes = context.socket(zmq.REP)
socket_clientes.connect("tcp://broker:5556")

pub = context.socket(zmq.PUB)
pub.connect("tcp://proxy:5557")

req_ref = context.socket(zmq.REQ)
req_ref.connect("tcp://broker2:5559")

berkeley_rep = context.socket(zmq.REP)
berkeley_rep.bind(f"tcp://*:{PORTA_BERKELEY}")

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

nome = pysocket.gethostname()
rank = -1

req_ref.send(msgpack.packb({"func": "rank", "name": nome}))
resposta = msgpack.unpackb(req_ref.recv())
rank = resposta["rank"]
print(f"Servidor {nome} recebeu o rank {rank}")

req_ref.send(msgpack.packb({"func": "listar", "name": nome}))
resposta = msgpack.unpackb(req_ref.recv())
print("Servidores ativos:", resposta["lista"])

contador_heartbeat = 0

# ── Eleição ───────────────────────────────────────────────────────────────────
coordenador = ""
ultimo_heartbeat_coord = 0.0
intervalo_heartbeat = 3
timeout_coordenador = 10
eleicao = False
existe_maior = False
timeout_eleicao = 0.0
startup_time = datetime.now().timestamp()
tempo_descoberta = 8 + rank * 2

# ── Berkeley ──────────────────────────────────────────────────────────────────
BERKELEY_INTERVALO = 15
contador_desde_sync = 0

sub_servers = context.socket(zmq.SUB)
sub_servers.connect("tcp://proxy:5558")
sub_servers.setsockopt_string(zmq.SUBSCRIBE, "servers")

poller = zmq.Poller()
poller.register(socket_clientes, zmq.POLLIN)
poller.register(sub_servers, zmq.POLLIN)
poller.register(berkeley_rep, zmq.POLLIN)

# ── Conjunto de IDs de mensagens já replicadas (deduplicação) ─────────────────
ids_mensagens = set()
for m in mensagens:
    ids_mensagens.add((m["user"], m["channel"], m["contador"]))


def iniciar_eleicao():
    global eleicao, existe_maior, timeout_eleicao
    print("[ELEICAO] Iniciando eleição")
    eleicao = True
    existe_maior = False
    timeout_eleicao = datetime.now().timestamp()
    pub.send_multipart([b"servers", msgpack.packb({
        "tipo": "Eleicao", "autor": nome, "rank": rank
    })])


def rodar_berkeley():
    global contador, contador_desde_sync
    contador_desde_sync = 0

    # Pega a lista atualizada de servidores na referência
    req_ref.send(msgpack.packb({"func": "listar", "name": nome}))
    resp = msgpack.unpackb(req_ref.recv())
    outros = [s["name"] for s in resp["lista"] if s["name"] != nome]

    print(f"[BERKELEY] Iniciando | meu contador={contador} | outros={outros}")

    # ── Fase 1: GET ──────────────────────────────────────────────────────────
    contadores = {nome: contador}
    for alvo in outros:
        req = context.socket(zmq.REQ)
        req.setsockopt(zmq.RCVTIMEO, 2000)  # timeout 2s por servidor
        req.connect(f"tcp://{alvo}:{PORTA_BERKELEY}")
        try:
            req.send(msgpack.packb({"func": "berkeley_get"}))
            r = msgpack.unpackb(req.recv())
            contadores[alvo] = r["contador"]
            print(f"[BERKELEY] GET {alvo}: contador={r['contador']}")
        except zmq.Again:
            print(f"[BERKELEY] GET {alvo}: timeout, ignorando")
        finally:
            req.close()

    if len(contadores) < 2:
        print("[BERKELEY] Menos de 2 respostas, abortando")
        return

    # ── Fase 2: SET ──────────────────────────────────────────────────────────
    media = sum(contadores.values()) / len(contadores)
    print(f"[BERKELEY] Contadores={contadores} | Média={media:.1f}")

    for alvo, valor in contadores.items():
        delta = round(media - valor)
        if alvo == nome:
            if delta != 0:
                contador += delta
                print(f"[BERKELEY] Meu ajuste: {valor} → {contador} (delta {delta:+d})")
            continue

        req = context.socket(zmq.REQ)
        req.setsockopt(zmq.RCVTIMEO, 2000)
        req.connect(f"tcp://{alvo}:{PORTA_BERKELEY}")
        try:
            req.send(msgpack.packb({"func": "berkeley_set", "delta": delta}))
            r = msgpack.unpackb(req.recv())
            print(f"[BERKELEY] SET {alvo}: delta={delta:+d} status={r['status']}")
        except zmq.Again:
            print(f"[BERKELEY] SET {alvo}: timeout")
        finally:
            req.close()


def replicar_mensagem(pub_msg):
    """Publica uma mensagem no canal 'servers' para replicação nos demais nós."""
    pub.send_multipart([b"servers", msgpack.packb({
        "tipo": "replicar",
        "autor": nome,
        "mensagem": pub_msg
    })])
    print(f"[REPLICACAO] Enviada para replicação: {pub_msg['user']} -> {pub_msg['channel']}")


# ── loop principal ────────────────────────────────────────────────────────────
while True:

    eventos = dict(poller.poll(1000))

    # ── Berkeley REP: responde GET e SET do coordenador ───────────────────
    if berkeley_rep in eventos:
        data = berkeley_rep.recv()
        msg  = msgpack.unpackb(data)
        func = msg["func"]

        if func == "berkeley_get":
            print(f"[BERKELEY] GET recebido | meu contador={contador}")
            berkeley_rep.send(msgpack.packb({"contador": contador}))

        elif func == "berkeley_set":
            delta = msg["delta"]
            antes = contador
            contador += delta
            print(f"[BERKELEY] SET recebido | {antes} → {contador} (delta {delta:+d})")
            berkeley_rep.send(msgpack.packb({"status": "ok"}))

    # ── mensagens de clientes ─────────────────────────────────────────────
    if socket_clientes in eventos:
        data = socket_clientes.recv()
        contador_heartbeat  += 1
        contador_desde_sync += 1
        msg = msgpack.unpackb(data)

        funcao   = msg["func"]
        user     = msg["user"]
        canal    = msg["channel"]
        tempo    = msg["time"]
        mensagem = msg["msg"]
        cont     = msg["contador"]

        if contador_heartbeat >= 10:
            req_ref.send(msgpack.packb({"func": "heartbeat", "name": nome}))
            resp_hb = msgpack.unpackb(req_ref.recv())
            print(f"[HEARTBEAT] enviado | Referencia: {resp_hb['status']}")
            contador_heartbeat = 0

        if cont > contador:
            contador = cont + 1

        if funcao == "login":
            if user in usuariosLogados:
                contador += 1
                socket_clientes.send(msgpack.packb({"situ": "erro-login", "contador": contador}))
                print(f"Erro login {user} as {tempo}", flush=True)
            else:
                if user not in usuarios:
                    usuarios.append(user)
                    salvar_dados()
                usuariosLogados.append(user)
                contador += 1
                socket_clientes.send(msgpack.packb({"situ": "success", "contador": contador}))
                print(f"Login {user} as {tempo}", flush=True)

        elif funcao == "entrar":
            if user not in usuariosLogados:
                contador += 1
                socket_clientes.send(msgpack.packb({"situ": "erro-semLogin", "contador": contador}))
            else:

                if canal not in canais:
                    canais.append(canal)
                    salvar_dados()
                    pub.send_multipart([b"servers", msgpack.packb({
                        "tipo": "replicar_canal",
                        "autor": nome,
                        "canal": canal
                    })])
                    print(f"[REPLICACAO] Canal enviado para replicação: {canal}")

                contador += 1
                socket_clientes.send(msgpack.packb({"situ": "success", "contador": contador}))
                print(f"Entrou/criou canal {canal} as {tempo}")

        elif funcao == "listar":
            if user not in usuariosLogados:
                contador += 1
                socket_clientes.send(msgpack.packb({"situ": "erro-semLogin", "contador": contador}))
            else:
                contador += 1
                socket_clientes.send(msgpack.packb({"situ": "success", "canais": canais, "contador": contador}))

        elif funcao == "publicar":
            contador += 1
            if user not in usuariosLogados:
                data_resp = {"situ": "erro-semLogin", "contador": contador}
            elif canal not in canais:
                data_resp = {"situ": "erro-canal", "contador": contador}
            else:
                pub_msg = {
                    "user": user, "channel": canal,
                    "msg": mensagem, "time": tempo, "contador": contador
                }
                # Publica para os clientes inscritos no canal
                pub.send_multipart([canal.encode(), msgpack.packb(pub_msg)])

                # Salva localmente
                chave = (user, canal, contador)
                if chave not in ids_mensagens:
                    mensagens.append(pub_msg)
                    ids_mensagens.add(chave)
                    salvar_mensagens()

                print(f"[PUB] {user} -> {canal}: {mensagem} ({tempo}) Relogio: {contador}", flush=True)

                # ── REPLICAÇÃO: propaga para os demais servidores ──────────
                replicar_mensagem(pub_msg)

                data_resp = {"situ": "success", "contador": contador}
                sleep(1)
            socket_clientes.send(msgpack.packb(data_resp))

        else:
            contador += 1
            socket_clientes.send(msgpack.packb({"situ": "erro-comando", "contador": contador}))
            print(f"Comando desconhecido as {tempo}", flush=True)

        # Coordenador dispara Berkeley a cada BERKELEY_INTERVALO mensagens
        if coordenador == nome and contador_desde_sync >= BERKELEY_INTERVALO:
            rodar_berkeley()

    # ── tópico "servers" ─────────────────────────────────────────────────
    if sub_servers in eventos:
        topico, dados = sub_servers.recv_multipart()
        msg   = msgpack.unpackb(dados)
        tipo  = msg["tipo"]
        autor = msg.get("autor", "")

        if autor == nome and tipo in ("Eleicao", "ok", "replicar","replicar_canal"):
            # Ignora mensagens que nós mesmos enviamos
            pass

        elif tipo == "replicar":
            # ── REPLICAÇÃO: recebe mensagem de outro servidor ──────────────
            pub_msg = msg["mensagem"]
            chave = (pub_msg["user"], pub_msg["channel"], pub_msg["contador"])
            if chave not in ids_mensagens:
                mensagens.append(pub_msg)
                ids_mensagens.add(chave)
                salvar_mensagens()
                # Garante que canais referenciados existam localmente
                if pub_msg["channel"] not in canais:
                    canais.append(pub_msg["channel"])
                    salvar_dados()
                print(f"[REPLICACAO] Recebida de {autor}: {pub_msg['user']} -> {pub_msg['channel']}: {pub_msg['msg']}")
            else:
                print(f"[REPLICACAO] Mensagem duplicada ignorada (contador={pub_msg['contador']})")

        elif tipo == "Eleicao":
            rank_eleicao = msg["rank"]
            print(f"[ELEICAO] Recebi de {autor} (rank {rank_eleicao}), meu rank: {rank}")
            if rank > rank_eleicao:
                pub.send_multipart([b"servers", msgpack.packb({
                    "tipo": "ok", "autor": nome, "para": autor
                })])
                if not eleicao:
                    iniciar_eleicao()

        elif tipo == "ok":
            if msg.get("para") == nome:
                print(f"[ELEICAO] Recebi OK de {autor}")
                existe_maior = True

        elif tipo == "Coordenador":
            novo_coord = msg["name"]
            rank_coord = msg["rank"]
            if rank_coord > rank or novo_coord == nome:
                coordenador = novo_coord
                eleicao     = False
                existe_maior = False
                ultimo_heartbeat_coord = datetime.now().timestamp()
                contador_desde_sync = 0
                print(f"[COORDENADOR ACEITO] {coordenador} (rank {rank_coord})")
            else:
                print(f"[IGNORADO] {novo_coord} rank {rank_coord} <= meu rank {rank}")

        elif tipo == "heartbeat":
            if msg["name"] == coordenador:
                ultimo_heartbeat_coord = datetime.now().timestamp()

        elif tipo == "replicar_canal":
            canal_novo = msg["canal"]
            if canal_novo not in canais:
                canais.append(canal_novo)
                salvar_dados()
                print(f"[REPLICACAO] Canal recebido de {autor}: {canal_novo}")

    # ── lógica periódica ─────────────────────────────────────────────────
    agora = datetime.now().timestamp()

    if eleicao and not existe_maior:
        if agora - timeout_eleicao > 3:
            print("[ELEICAO] Timeout — sou o novo coordenador!")
            coordenador = nome
            eleicao     = False
            existe_maior = False
            ultimo_heartbeat_coord = agora
            contador_desde_sync = 0
            pub.send_multipart([b"servers", msgpack.packb({
                "tipo": "Coordenador", "autor": nome, "name": nome, "rank": rank
            })])

    if coordenador == nome:
        if agora - ultimo_heartbeat_coord > intervalo_heartbeat:
            pub.send_multipart([b"servers", msgpack.packb({
                "tipo": "heartbeat", "autor": nome, "name": nome
            })])
            print("[HEARTBEAT] Coordenador vivo")
            ultimo_heartbeat_coord = agora

    if coordenador == "" and not eleicao and agora - startup_time > tempo_descoberta:
        print("[STARTUP] Nenhum coordenador encontrado, iniciando eleição")
        iniciar_eleicao()

    elif coordenador != nome and coordenador != "" and not eleicao:
        if agora - ultimo_heartbeat_coord > timeout_coordenador:
            print(f"[FALHA] Coordenador {coordenador} não responde!")
            coordenador = ""
            iniciar_eleicao()

