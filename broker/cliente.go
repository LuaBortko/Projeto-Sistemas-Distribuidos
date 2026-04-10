package main

import (
	"fmt"
	"time"

	"github.com/pebbe/zmq4"
	"github.com/vmihailenco/msgpack/v5"
)

type Message struct {
	User    string `msgpack:"user"`
	Func    string `msgpack:"func"`
	Channel string `msgpack:"channel"`
	Time    string `msgpack:"time"`
	Msg     string `msgpack:"msg"`

}

func mandar(socket *zmq4.Socket, funcao string, user string, channel string, mensagem string) {
	location, _ := time.LoadLocation("America/Sao_Paulo")
	tempo := time.Now().In(location).Format("15:04")
	msg := Message{
		User:    user,
		Func:    funcao,
		Channel: channel,
		Time:    tempo,
		Msg:     mensagem,
	}
	fmt.Printf("Mensagem do usuario em %s. Mensagem: %+v\n", tempo, msg)
	packet, _ := msgpack.Marshal(msg)
	socket.SendBytes(packet, 0)
}

func receber(socket *zmq4.Socket) {
	bytes, _ := socket.RecvBytes(0)
	var resposta interface{}
	msgpack.Unmarshal(bytes, &resposta)
	fmt.Printf("Resposta do servidor: %+v\n", resposta)
}

func main() {
	socket, _ := zmq4.NewSocket(zmq4.REQ)
	defer socket.Close()
	socket.Connect("tcp://broker:5555")
	sub, _ := zmq4.NewSocket(zmq4.SUB)
	sub.Connect("tcp://pubsub-proxy:5558")
	for {
		mandar(socket, "login", "go1", "", "")
		receber(socket)
		time.Sleep(2 * time.Second)

		mandar(socket, "entrar", "go1", "CanalGo", "")
		receber(socket)
		sub.SetSubscribe("CanalGo")
		time.Sleep(2 * time.Second)

		//mandar(socket, "listar", "go2", "", "")
		//receber(socket)
		//time.Sleep(2 * time.Second)

		mandar(socket, "listar", "go1", "", "")
		receber(socket)
		time.Sleep(2 * time.Second)

	}
	go func() {
    	for {
        	frames, _ := sub.RecvMessageBytes(0)
    	    canal := string(frames[0])
        	data := frames[1]
        	var msg interface{}
        	msgpack.Unmarshal(data, &msg)
			fmt.Println("Mensagem recebida:", canal, msg)
    	}
	}()
}
