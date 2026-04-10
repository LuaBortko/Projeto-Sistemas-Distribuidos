# Projeto: Sistema para troca de mensagem instantânea

O Bulletin Board System (BBS) surgiu no final da década de 1970, permitindo que usuários se conectassem a servidores para acessar notícias, participar de discussões e trocar mensagens. No final da década de 1980, foi desenvolvido o Internet Relay Chat (IRC), que incorporou parte dessas funcionalidades. Embora os BBS tenham desaparecido na década de 1990 e o IRC tenha perdido popularidade ao longo do tempo, esses sistemas serviram de base para muitos serviços modernos de comunicação.

Este projeto propõe o desenvolvimento de uma versão simplificada de um sistema desse tipo, utilizando conceitos estudados na disciplina de Sistemas Distribuídos. O sistema permitirá que usuários (bots) publiquem mensagens em canais públicos, com todas as interações armazenadas em disco para possibilitar a recuperação de mensagens anteriores. Além disso, o sistema deverá permitir a adição e remoção de servidores sem interrupção do serviço.

## Linguagens
- **Python**: Linguagem escolhida por ser uma linguagem que estou bem familiarizada, e tambem por ser a linguagem utilizada nos exemplos nas aulas, e sera usada no servidor do projeto
- **Golang**: Linguagem escolhida pois queria uma em que eu não tivesse muito conhecimento, para treinar a utilização dela durante o projeto e por ela tem todas as bibliotecas necessarias para a implementação do projeto de facil acesso, essa linguagem será usada no cliente do projeto

## Serialização
O formato escolhido para a troca de mensagens foi o **MessagePack**, por ser um formato simples e eficiente. Além disso, ele possui suporte tanto em Python, por meio da biblioteca msgpack, quanto em Go, utilizando a biblioteca github.com/vmihailenco/msgpack/v5.

## Persistência dos dados
O formato escolhido foi com a biblioteca **pickle**, que é uma biblioteca nativa usada para serializar (converter em bytes) e desserializar (reconstruir) objetos Python, como dicionários, listas e modelos de IA. Ele salva dados complexos em um arquivo .pkl.
