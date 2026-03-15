package main

import (
	"fmt"

	"github.com/pebbe/zmq4"
	"github.com/vmihailenco/msgpack/v5"
)

type Message struct {
	User    string `msgpack:"user"`
	Func    string `msgpack:"func"`
	Channel string `msgpack:"channel"`
	Time    string `msgpack:"time"`
}

type Response struct {
	Situ string `msgpack:"situ"`
}

func contains(slice []string, item string) bool {
	for _, v := range slice {
		if v == item {
			return true
		}
	}
	return false
}

func main() {

	socket, _ := zmq4.NewSocket(zmq4.DEALER)
	defer socket.Close()

	socket.Connect("tcp://broker:5556")

	usuarios := []string{}
	usuariosLogados := []string{}
	canais := []string{}

	fmt.Println("Servidor Go conectado ao broker")

	for {

		frames, _ := socket.RecvMessageBytes(0)
		data := frames[len(frames)-1]

		var msg Message
		msgpack.Unmarshal(data, &msg)

		funcao := msg.Func
		user := msg.User
		canal := msg.Channel
		tempo := msg.Time

		var resp Response

		if funcao == "login" {

			if contains(usuariosLogados, user) {

				resp = Response{"erro-login"}

				fmt.Printf(
					"Erro ao entrar no servidor as %s, usuario ja logado\n",
					tempo,
				)

			} else {

				if !contains(usuarios, user) {
					usuarios = append(usuarios, user)
				}

				usuariosLogados = append(usuariosLogados, user)

				resp = Response{"success"}

				fmt.Printf(
					"O usuario %s entrou no servidor com sucesso as %s\n",
					user,
					tempo,
				)
			}

		} else if funcao == "entrar" {

			if !contains(usuariosLogados, user) {

				resp = Response{"erro-semLogin"}

				fmt.Printf(
					"O usuario %s não esta logado, tentativa de acesso as %s\n",
					user,
					tempo,
				)

			} else {

				if !contains(canais, canal) {

					canais = append(canais, canal)

					resp = Response{"success"}

					fmt.Printf(
						"Canal não encontrado, criado novo canal com o nome %s as %s\n",
						canal,
						tempo,
					)

				} else {

					resp = Response{"success"}

					fmt.Printf(
						"Entrou no canal %s com sucesso! as %s\n",
						canal,
						tempo,
					)
				}
			}

		} else if funcao == "listar" {

			if !contains(usuariosLogados, user) {

				resp = Response{"erro-semLogin"}

				fmt.Printf(
					"O usuario %s não esta logado, tentativa de acesso as %s\n",
					user,
					tempo,
				)

			} else {

				resp = Response{"success"}

				fmt.Println(canais)
			}

		} else {

			resp = Response{"erro-comando"}

		}

		packet, _ := msgpack.Marshal(resp)

		socket.SendMessage(append(frames[:len(frames)-1], packet))
	}
}
