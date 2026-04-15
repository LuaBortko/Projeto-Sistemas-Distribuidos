package main

import (
	"fmt"
	"time"
	"math/rand"
	
	"github.com/pebbe/zmq4"
	"github.com/vmihailenco/msgpack/v5"
)

type Message struct {
	User    string `msgpack:"user"`
	Func    string `msgpack:"func"`
	Channel string `msgpack:"channel"`
	Time    string `msgpack:"time"`
	Msg     string `msgpack:"msg"`
	Contador string `msgpack:"contador"`

}

type Listar struct {
	Situ   string   `msgpack:"situ"`
	Canais []string `msgpack:"canais"`
	Msg     string `msgpack:"msg"`
	Contador string `msgpack:"contador"`
}

func mandar(socket *zmq4.Socket, funcao string, user string, channel string, mensagem string, contador *int){
	//contador =+ 1 
	location, _ := time.LoadLocation("America/Sao_Paulo")
	tempo := time.Now().In(location).Format("15:04")
	msg := Message{
		User:    user,
		Func:    funcao,
		Channel: channel,
		Time:    tempo,
		Msg:     mensagem,
		//Contador: contador,
	}
	fmt.Printf("Mensagem do usuario em %s. Mensagem: %+v\n", tempo, msg)
	packet, _ := msgpack.Marshal(msg)
	socket.SendBytes(packet, 0)
}

func receber(socket *zmq4.Socket, contador *int) {
	bytes, _ := socket.RecvBytes(0)
	var resposta interface{}
	msgpack.Unmarshal(bytes, &resposta)
	//pegar o contador da mensagem e verificar, se for maior que o daqui eu substituo e somo 1, senão não faço nada
	fmt.Printf("Resposta do servidor: %+v\n", resposta)
}

func contains(slice []string, item string)bool{
	for _,v := range slice{
		if v == item{
			return true
		}
	}
	return false
}

func garantirInscricao(socket *zmq4.Socket, user string,canais []string,inscritos *[]string,sub *zmq4.Socket, contador *int) {
	for len(*inscritos) < 3 {
		canal := canais[rand.Intn(len(canais))]
		if !contains(*inscritos, canal) {
			mandar(socket, "entrar", user, canal, "", contador)
			receber(socket, contador)
			sub.SetSubscribe(canal)
			*inscritos = append(*inscritos, canal)
			fmt.Println("Inscrito em:", canal)
		}
	}
}

func listarCanais(socket *zmq4.Socket, user string, contador *int) []string {

	mandar(socket, "listar", user, "", "", contador)
	bytes, _ := socket.RecvBytes(0)
	var resp Listar
	msgpack.Unmarshal(bytes, &resp)

	if resp.Situ != "success" {
		fmt.Println("Erro ao listar canais")
		return []string{}
	}

	return resp.Canais
}

func garantirCanais(socket *zmq4.Socket, user string, contador *int) []string {

	canais := listarCanais(socket, user, contador)

	for len(canais) < 5 {

		novo := fmt.Sprintf("canal%d", rand.Intn(100))

		mandar(socket, "entrar", user, novo, "", contador)
		receber(socket, contador)

		canais = listarCanais(socket, user, contador)
	}

	return canais
}

func termoAleatorio( lista []string) string{
	return lista[rand.Intn(len(lista))] 
}

func main() {
	contador = 0
	socket, _ := zmq4.NewSocket(zmq4.REQ)
	defer socket.Close()
	socket.Connect("tcp://broker:5555")
	sub, _ := zmq4.NewSocket(zmq4.SUB)
	sub.Connect("tcp://proxy:5558")
	
	rand.Seed(time.Now().UnixNano())
	numero := rand.Intn(100)
	user := fmt.Sprintf("bot%d", numero)

	var canais []string        // canais existentes
	var inscritos []string     // canais que o bot entrou
	msgs := []string{
		"oiii",
		"quero me matar",
		"faz o L",
		"67 -> vou me atirar do prédio do K",
		"divou",
		"babilonico",
		"Eu sei que você já é casado",
		"Mas me diz o que fazeerrr",
		"Aquela barata cascuda!",
		"AAAAAAAAAAAAAAAAAAAAAAAH",
		"Na minha máquina funciona",
		"Odeio vans escolares",
		"Me diga então... diga então",
		"Parei",
		"não não",
		"cs?",
		"Rapaiz",
	}

	//Login
	time.Sleep(2 * time.Second)
	mandar(socket, "login", user, "", "", contador)
	receber(socket, contador)
	time.Sleep(2 * time.Second)

	canais = garantirCanais(socket, user, contador)
	garantirInscricao(socket, user, canais, &inscritos, sub, contador) // garanto que pelo menos há 3 inscrições

	//Roda simultaneo, para sempre receber as mensagens do publisher
	go func() {
    		for {
        		frames, _ := sub.RecvMessageBytes(0)
    	    		canal := string(frames[0])
        		data := frames[1]
        		var msg interface{}
        		msgpack.Unmarshal(data, &msg)
			fmt.Println("Usuario: ", user)
			fmt.Println("Mensagem recebida: ", canal, msg)

	//pegar o contador da mensagem e verificar, se for maior que o daqui eu substituo e somo 1, senão não faço nada
    		}
	}()


	for {
		
		mandar(socket, "publicar", user, termoAleatorio(canais), termoAleatorio(msgs), contador)
    		receber(socket, contador)
		
	}
}
