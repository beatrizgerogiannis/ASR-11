# Serviço de Nomes + Serviços de Aplicação em gRPC (Python)

Trabalho de Sistemas Distribuídos (UFG, prof. Fábio). Partindo do
[gRPC-SimpleNamingService](https://github.com/professorfabio/gRPC-SimpleNamingService)
do professor, este repositório implementa:

1. **Serviço de nomes** em gRPC com `Bind`, `Lookup`, `Unbind` e `Rebind`;
2. **Dois serviços de aplicação** em gRPC, cada um no seu processo/máquina:
   **Calculadora** (`Add`, `Sub`, `Mul`, `Div`) e **Texto** (`Upper`, `Reverse`, `CountWords`, `Analyze`);
3. **Cliente** que conhece apenas o endereço do serviço de nomes, descobre os serviços por
   `Lookup` e chama os RPCs;
4. Execução em **processos separados** (local) e em **"máquinas" diferentes** simuladas com Docker
   (um container por papel, cada um com seu IP).

## Arquitetura

```
                       +------------------------------+
                       |   Serviço de Nomes  (:5678)  |
                       |   { nome -> (ip, porta) }    |
                       +------------------------------+
                          ^              ^         ^
       (2) Lookup(nome)   |              |         |   (1) Bind (ou Rebind) ao iniciar
           -> ip:porta    |              |         |   (5) Unbind ao encerrar
                          |   +----------+--+  +---+----------+
     +-----------+        |   | Calculadora |  |    Texto     |
     |  Cliente  |--------+   |   (:50051)  |  |   (:50061)   |
     |           |            | Add Sub     |  | Upper Reverse|
     |           |----(3)---->| Mul Div     |  | CountWords   |
     |           |----(3)------------------->| Analyze      |
     +-----------+            +-------------+  +--------------+

  (3) o cliente chama os RPCs direto no endereço devolvido pelo Lookup
  (4) se uma chamada falhar (UNAVAILABLE/timeout): novo Lookup e uma nova tentativa
```

No Docker (rede `172.30.10.0/24`):

| Container      | IP             | Porta | Papel                                   |
|----------------|----------------|-------|-----------------------------------------|
| `nomes`        | 172.30.10.10   | 5678  | serviço de nomes                        |
| `calculadora`  | 172.30.10.20   | 50051 | serviço 1                               |
| `calculadora2` | 172.30.10.21   | 50052 | nova instância da Calculadora (migração)|
| `texto`        | 172.30.10.30   | 50061 | serviço 2                               |
| `cliente`      | 172.30.10.40   | —     | cliente                                 |

## Estrutura

```
protos/
  SimpleNamingService.proto   serviço de nomes (do professor, sem alterações)
  Calculadora.proto           serviço 1
  Texto.proto                 serviço 2
python/
  SimpleNamingService.py      servidor de nomes (corrigido)
  CalculadoraService.py       servidor da Calculadora
  TextoService.py             servidor de Texto
  nomes_cliente.py            funções comuns: lookup, registro (bind/rebind/unbind), ciclo de vida dos servidores
  cliente.py                  cliente (--demo, interativo ou comando único)
  testNS.py                   teste original do professor (sem alterações)
  testErrosNS.py              teste dos casos de erro do serviço de nomes
  const.py                    endereço padrão do serviço de nomes
  *_pb2.py, *_pb2.pyi, *_pb2_grpc.py   código gerado pelo protoc (versionado)
gerar_codigo.sh               gera o código Python de todos os .proto
demo_local.sh                 demonstração com processos locais
Dockerfile, docker-compose.yml, demo_docker.sh   demonstração com containers
```

## O que veio do professor e o que mudou

**Veio do professor:** `SimpleNamingService.proto`, `SimpleNamingService.py` (servidor de nomes
com `nameDB` em lista), `testNS.py` e `const.py`.

**Corrigido no serviço de nomes** (sem mudar o `.proto`):

| Problema no original | Comportamento agora |
|---|---|
| `Rebind` de nome inexistente: `IndexError` no servidor; o cliente recebe `StatusCode.UNKNOWN` | responde `NOK: nome não registrado; use Bind` |
| `Bind` de nome já existente cria duplicata (e a duplicata sobrevive ao `Unbind`) | recusa com `NOK: nome já registrado em ip:porta; use Rebind` |
| `nameDB` (lista) acessado por até 10 threads sem sincronização | `dict` protegido por `threading.Lock` |
| `Bind` aceitava nome/endereço vazio | recusa com `NOK: nome vazio` / `NOK: endereço incompleto` |
| sem log | log de cada operação: operação, nome, endereço, resultado e IP de quem chamou |
| IP do servidor fixo (AWS do professor) em `const.py` | padrão `localhost`; configurável por `NS_HOST`/`NS_PORT` ou `--ns-host`/`--ns-porta` |
| `Ctrl+C` gera traceback | encerra de forma limpa com `SIGINT`/`SIGTERM` |

Reprodução dos problemas no código original (saída real, servidor original rodando em localhost):

```
Bind X -> OK
Bind X de novo -> OK
Unbind X -> OK
Lookup X após unbind (duplicata sobrou) -> ipaddress: "10.0.0.2"
portnumber: "2"

Rebind NaoExiste -> StatusCode.UNKNOWN | Exception calling application: list index out of range
```

**Acrescentado:** os dois serviços de aplicação (`.proto` + servidores), o cliente, o módulo
`nomes_cliente.py`, o teste `testErrosNS.py`, scripts e arquivos Docker.

O `testNS.py` original continua funcionando sem nenhuma alteração (saídas abaixo).

## Os `.proto`

| Serviço (arquivo) | RPC | Requisição | Resposta | Erros |
|---|---|---|---|---|
| `SimpleNamingService` (`SimpleNamingService.proto`) | `Bind` | `BindMsg{name, address}` | `StatusMsg{status}` | `status = "NOK: ..."` se o nome já existe ou se faltam dados |
| | `Rebind` | `BindMsg` | `StatusMsg` | `"NOK: ..."` se o nome não existe |
| | `Unbind` | `NameMsg{name}` | `StatusMsg` | `"NOK: nome não registrado"` |
| | `Lookup` | `NameMsg` | `AddressMsg{ipaddress, portnumber}` | nome inexistente → endereço vazio (`''`, `''`) |
| `Calculadora` (`Calculadora.proto`) | `Add`, `Sub`, `Mul`, `Div` | `OperandosMsg{double a, double b}` | `ResultadoMsg{double valor, string expressao, string servidor}` | `Div` com `b = 0` → gRPC `INVALID_ARGUMENT` ("divisão por zero") |
| `Texto` (`Texto.proto`) | `Upper`, `Reverse` | `TextoMsg{texto}` | `TextoMsg` | — |
| | `CountWords` | `TextoMsg` | `ContagemMsg{int32 palavras}` | — |
| | `Analyze` | `TextoMsg` | `AnaliseMsg` (abaixo) | — |

`AnaliseMsg` usa campos de tipos variados: `int32 caracteres, palavras, linhas, vogais`,
`double tamanho_medio_palavra`, `string palavra_mais_longa`, `bool palindromo` (ignora
espaços, pontuação, acentos e maiúsculas), `repeated FrequenciaMsg mais_frequentes`
(até 5 pares `palavra`/`ocorrencias`) e `string servidor`.

O campo `servidor` das respostas traz o endereço anunciado da instância que atendeu; serve para
ver a migração acontecendo.

## Semântica do serviço de nomes

Em todos os casos `status` é exatamente `"OK"` em caso de sucesso (como no original) ou
`"NOK: <motivo>"` em caso de erro. Os erros são devolvidos no `StatusMsg` e não como erro gRPC,
para manter a interface e o `testNS.py` como estavam.

- **Bind(nome, endereço)**: registra o nome. Se o nome já existe, **recusa** (`NOK ... use Rebind`)
  e não altera o registro. Nome, IP e porta são obrigatórios.
- **Lookup(nome)**: devolve o endereço registrado. Se o nome não existe, devolve
  **endereço vazio** (`ipaddress=''`, `portnumber=''`), como no original. Não usamos
  `context.set_code(NOT_FOUND)` porque isso faria o stub levantar exceção e quebraria clientes
  antigos como o `testNS.py`; quem chama deve tratar endereço vazio como "não encontrado"
  (é o que `nomes_cliente.ClienteNomes.lookup` faz, devolvendo `None`).
- **Unbind(nome)**: remove o registro; `NOK: nome não registrado` se não existir.
- **Rebind(nome, endereço)**: atualiza o endereço de um nome **existente**. Decisão: Rebind de
  nome inexistente é **erro** (`NOK ... use Bind`), e não cria o registro. Assim Bind = criar e
  Rebind = atualizar, e um Rebind com nome digitado errado não cria um registro novo sem aviso.
  O endereço anterior aparece no log do servidor.

**Ciclo de vida dos servidores de aplicação** (`nomes_cliente.executar_servidor`):

1. sobe o gRPC na porta (`--porta`, ouvindo em `[::]`);
2. faz `Bind(nome, ip_anunciado:porta)`; se o nome já existir, faz `Rebind`.
   O IP anunciado vem de `--anunciar` (ou `ANUNCIAR_IP`); sem ele, usa o IP local da interface
   que alcança o serviço de nomes. Não se anuncia `0.0.0.0`, que não é um endereço útil para o
   cliente;
3. em `Ctrl+C`/`SIGTERM`, faz `Lookup` do próprio nome e só faz `Unbind` se o registro ainda
   apontar para ele. Se outra instância já tiver feito `Rebind` (migração), o registro não é
   removido.

**Cliente** (`cliente.py`): faz `Lookup`, guarda o endereço em cache e abre o canal. Se uma
chamada falha com `UNAVAILABLE` ou `DEADLINE_EXCEEDED` (timeout de 2 s), refaz o `Lookup`
**uma vez** e tenta de novo. Serviço não registrado, serviço fora do ar, serviço de nomes fora
do ar e erros como `INVALID_ARGUMENT` são mostrados como mensagem, sem traceback.

## Como rodar

### Ambiente e geração de código

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./gerar_codigo.sh        # roda python -m grpc_tools.protoc para cada protos/*.proto
```

**Código gerado versionado:** os arquivos `*_pb2.py`, `*_pb2.pyi` e `*_pb2_grpc.py` ficam no
repositório, para que quem clonar (e a imagem Docker) rode direto, sem o `protoc`. Ao alterar um
`.proto`, rode `./gerar_codigo.sh` e versione os arquivos gerados junto. O código gerado exige
a versão de `protobuf` do `requirements.txt` (ou mais nova).

### Local, cada papel num terminal

```bash
cd python
../.venv/bin/python SimpleNamingService.py                                      # terminal 1
../.venv/bin/python CalculadoraService.py --porta 50051 --anunciar 127.0.0.1    # terminal 2
../.venv/bin/python TextoService.py --porta 50061 --anunciar 127.0.0.1          # terminal 3
../.venv/bin/python cliente.py --demo                                           # terminal 4
../.venv/bin/python cliente.py                  # modo interativo (add 2 3, upper oi, lookup Texto, sair)
../.venv/bin/python cliente.py div 1 0          # comando único
../.venv/bin/python testNS.py                   # teste original do professor
```

Para **migrar** a Calculadora: com a primeira instância no ar, suba outra em outra porta
(`CalculadoraService.py --porta 50052 --anunciar 127.0.0.1`). O `Bind` dela é recusado e ela faz
`Rebind`. Depois encerre a primeira com `Ctrl+C`.

Em máquinas diferentes: no serviço use `--ns-host <IP do serviço de nomes> --anunciar <IP desta máquina>`;
no cliente, `--ns-host <IP do serviço de nomes>` (ou `export NS_HOST=...`).

Tudo de uma vez, em background, com logs em `logs/`: **`./demo_local.sh`**.

### Docker (simulando máquinas diferentes)

```bash
./demo_docker.sh
```

O script usa o projeto compose `asr-grpc-sd` (não mexe em outros containers) e:

1. constrói a imagem (`python:3.12-slim` + `requirements.txt` + `python/`);
2. sobe `nomes`, `calculadora` e `texto`; cada serviço faz `Bind` com o IP do próprio container;
3. sobe o `cliente` com `--demo --esperar-migracao 60`;
4. **rebind:** sobe `calculadora2` (172.30.10.21:50052), que faz `Bind` → recusado → `Rebind`,
   e para a `calculadora` antiga; o cliente percebe a falha, refaz o `Lookup` e continua;
5. **unbind:** para o `texto` (que faz `Unbind`) e mostra que o cliente não o encontra mais;
6. roda o `testNS.py` original do container cliente para o serviço de nomes;
7. mostra os logs de todos os containers e derruba tudo (`docker compose down`).

Uso manual: `docker compose up -d nomes calculadora texto` e
`docker compose run --rm cliente python cliente.py` (interativo).

## Saídas reais dos testes

### Exemplo original (servidor e `testNS.py` do professor, sem alterações, em localhost)

```
Added new name binding OK
Returned IP address: 3.232.34.176 and port number: 5679
Added new name binding OK
Returned IP address: 34.203.80.210 and port number: 5680
Removed name binding OK
Returned IP address:  and port number:
```

O `testNS.py` dá a mesma saída contra o novo serviço de nomes, tanto local quanto no Docker.

### Casos de erro do serviço de nomes (`testErrosNS.py`)

```
Bind X 10.0.0.1:1           -> OK
Bind X 10.0.0.2:2 (repetido) -> NOK: nome já registrado em 10.0.0.1:1; use Rebind
Rebind X 10.0.0.2:2         -> OK
Lookup X                    -> 10.0.0.2:2
Unbind X                    -> OK
Lookup X (após unbind)      -> '':'' (vazio = não encontrado)
Unbind X (de novo)          -> NOK: nome não registrado
Rebind NaoExiste            -> NOK: nome não registrado; use Bind
Bind Y sem endereço         -> NOK: endereço incompleto (ipaddress e portnumber são obrigatórios)
```

### Docker: `./demo_docker.sh`

IPs dos containers:

```
asr-grpc-sd-nomes-1         172.30.10.10
asr-grpc-sd-calculadora-1   172.30.10.20
asr-grpc-sd-calculadora2-1  172.30.10.21
asr-grpc-sd-texto-1         172.30.10.30
asr-grpc-sd-cliente-1       172.30.10.40
```

Cliente (`172.30.10.40`):

```
[cliente] serviço de nomes: 172.30.10.10:5678 | IP deste cliente: 172.30.10.40

=== 1. Lookup dos serviços ===
[cliente] Lookup('Calculadora') -> 172.30.10.20:50051
[cliente] Lookup('Texto') -> 172.30.10.30:50061

=== 2. Calculadora ===
[cliente] Calculadora.Add: 7 + 5 = 12   (atendido por 172.30.10.20:50051)
[cliente] Calculadora.Sub: 7 - 5 = 2   (atendido por 172.30.10.20:50051)
[cliente] Calculadora.Mul: 7 * 5 = 35   (atendido por 172.30.10.20:50051)
[cliente] Calculadora.Div: 7 / 2 = 3.5   (atendido por 172.30.10.20:50051)

=== 3. Erro: divisão por zero (INVALID_ARGUMENT) ===
[cliente] ! Calculadora.Div recusado pelo servidor: INVALID_ARGUMENT: divisão por zero

=== 4. Texto ===
[cliente] Texto.Upper('Socorram-me, subi no ônibus em Marrocos') -> 'SOCORRAM-ME, SUBI NO ÔNIBUS EM MARROCOS'
[cliente] Texto.Reverse('Socorram-me, subi no ônibus em Marrocos') -> 'socorraM me subinô on ibus ,em-marrocoS'
[cliente] Texto.CountWords('Socorram-me, subi no ônibus em Marrocos') -> 7 palavras
[cliente] Texto.Analyze('o rato roeu a roupa do rei de Roma\ne o rei roeu o resto')   (atendido por 172.30.10.30:50061)
            caracteres             55
            palavras               15
            linhas                 2
            vogais                 26
            tamanho_medio_palavra  2.73
            palavra_mais_longa     roupa
            palindromo             False
            mais_frequentes        o(3), roeu(2), rei(2), rato(1), a(1)
[cliente] Texto.Analyze('Socorram-me, subi no ônibus em Marrocos')   (atendido por 172.30.10.30:50061)
            caracteres             39
            palavras               7
            linhas                 1
            vogais                 14
            tamanho_medio_palavra  4.57
            palavra_mais_longa     socorram
            palindromo             True
            mais_frequentes        socorram(1), me(1), subi(1), no(1), ônibus(1)

=== 5. Lookup de um serviço que não existe ===
[cliente] ! Lookup('Impressora'): serviço não registrado no serviço de nomes

=== 6. Migração: aguardando a Calculadora mudar de endereço (até 60s) ===
[cliente] endereço atual em cache: 172.30.10.20:50051
[cliente] Calculadora.Add: 1 + 100 = 101   (atendido por 172.30.10.20:50051)
[cliente] Calculadora.Add: 2 + 100 = 102   (atendido por 172.30.10.20:50051)
[cliente] Calculadora.Add: 3 + 100 = 103   (atendido por 172.30.10.20:50051)
[cliente] Calculadora.Add: 4 + 100 = 104   (atendido por 172.30.10.20:50051)
[cliente] Calculadora.Add: 5 + 100 = 105   (atendido por 172.30.10.20:50051)
[cliente] Calculadora.Add: 6 + 100 = 106   (atendido por 172.30.10.20:50051)
[cliente] ! Calculadora em 172.30.10.20:50051 não respondeu (DEADLINE_EXCEEDED)
[cliente] ! refazendo Lookup, o endereço pode ter mudado (rebind)...
[cliente] Lookup('Calculadora') -> 172.30.10.21:50052
[cliente] Calculadora.Add: 7 + 100 = 107   (atendido por 172.30.10.21:50052)
[cliente] MIGRAÇÃO OBSERVADA: Calculadora passou de 172.30.10.20:50051 para 172.30.10.21:50052; o cliente continuou funcionando após novo Lookup.
```

Unbind do Texto e nova tentativa de uso:

```
[cliente] serviço de nomes: 172.30.10.10:5678 | IP deste cliente: 172.30.10.40
[cliente] ! Lookup('Texto'): serviço não registrado no serviço de nomes
```

Serviço de nomes (`172.30.10.10`). A coluna `de` mostra o IP de quem fez a chamada:

```
00:11:39 [Nomes] Serviço de nomes ouvindo na porta 5678
00:11:39 [Nomes] Bind   nome='Texto'      endereco=172.30.10.30:50061    -> OK (de 172.30.10.30:59218)
00:11:39 [Nomes] Bind   nome='Calculadora' endereco=172.30.10.20:50051    -> OK (de 172.30.10.20:58158)
00:11:40 [Nomes] Lookup nome='Calculadora' -> 172.30.10.20:50051 (de 172.30.10.40:34062)
00:11:40 [Nomes] Lookup nome='Texto'      -> 172.30.10.30:50061 (de 172.30.10.40:34062)
00:11:40 [Nomes] Lookup nome='Impressora' -> não encontrado, devolve endereço vazio (de 172.30.10.40:34062)
00:11:44 [Nomes] Bind   nome='Calculadora' endereco=172.30.10.21:50052    -> NOK: nome já registrado em 172.30.10.20:50051; use Rebind (de 172.30.10.21:34728)
00:11:44 [Nomes] Rebind nome='Calculadora' endereco=172.30.10.21:50052    -> OK [antes: 172.30.10.20:50051] (de 172.30.10.21:34728)
00:11:46 [Nomes] Lookup nome='Calculadora' -> 172.30.10.21:50052 (de 172.30.10.20:58158)
00:11:48 [Nomes] Lookup nome='Calculadora' -> 172.30.10.21:50052 (de 172.30.10.40:34062)
00:11:49 [Nomes] Lookup nome='Texto'      -> 172.30.10.30:50061 (de 172.30.10.30:59218)
00:11:49 [Nomes] Unbind nome='Texto'      endereco=172.30.10.30:50061    -> OK (de 172.30.10.30:59218)
00:11:50 [Nomes] Lookup nome='Texto'      -> não encontrado, devolve endereço vazio (de 172.30.10.40:55122)
00:11:51 [Nomes] Bind   nome='AppSvcName123' endereco=3.232.34.176:5679     -> OK (de 172.30.10.40:55130)
00:11:51 [Nomes] Lookup nome='AppSvcName123' -> 3.232.34.176:5679 (de 172.30.10.40:55130)
00:11:51 [Nomes] Rebind nome='AppSvcName123' endereco=34.203.80.210:5680    -> OK [antes: 3.232.34.176:5679] (de 172.30.10.40:55130)
00:11:51 [Nomes] Lookup nome='AppSvcName123' -> 34.203.80.210:5680 (de 172.30.10.40:55130)
00:11:51 [Nomes] Unbind nome='AppSvcName123' endereco=34.203.80.210:5680    -> OK (de 172.30.10.40:55130)
00:11:51 [Nomes] Lookup nome='AppSvcName123' -> não encontrado, devolve endereço vazio (de 172.30.10.40:55130)
00:11:52 [Nomes] Lookup nome='Calculadora' -> 172.30.10.21:50052 (de 172.30.10.21:34728)
00:11:52 [Nomes] Unbind nome='Calculadora' endereco=172.30.10.21:50052    -> OK (de 172.30.10.21:34728)
```

Calculadora antiga (`172.30.10.20`) e nova (`172.30.10.21`):

```
00:11:39 [Calculadora] Servidor ouvindo em [::]:50051, anunciando 172.30.10.20:50051
00:11:39 [Calculadora] Bind(Calculadora, 172.30.10.20:50051) no serviço de nomes 172.30.10.10:5678 -> OK
00:11:40 [Calculadora] 7 + 5 = 12  (de 172.30.10.40:52140)
...
00:11:40 [Calculadora] 7 / 0 -> INVALID_ARGUMENT  (de 172.30.10.40:52140)
...
00:11:45 [Calculadora] 6 + 100 = 106  (de 172.30.10.40:52140)
00:11:46 [Calculadora] Encerrando...
00:11:46 [Calculadora] Unbind não feito: Calculadora agora aponta para 172.30.10.21:50052 (outra instância)

00:11:44 [Calculadora] Servidor ouvindo em [::]:50052, anunciando 172.30.10.21:50052
00:11:44 [Calculadora] Bind(Calculadora, 172.30.10.21:50052) no serviço de nomes 172.30.10.10:5678 -> NOK: nome já registrado em 172.30.10.20:50051; use Rebind
00:11:44 [Calculadora] Rebind(Calculadora, 172.30.10.21:50052) -> OK
00:11:48 [Calculadora] 7 + 100 = 107  (de 172.30.10.40:39266)
00:11:52 [Calculadora] Encerrando...
00:11:52 [Calculadora] Unbind(Calculadora) -> OK
```

Texto (`172.30.10.30`):

```
00:11:39 [Texto] Servidor ouvindo em [::]:50061, anunciando 172.30.10.30:50061
00:11:39 [Texto] Bind(Texto, 172.30.10.30:50061) no serviço de nomes 172.30.10.10:5678 -> OK
00:11:40 [Texto] Upper('Socorram-me, subi no ônibus em Marrocos') -> 'SOCORRAM-ME, SUBI NO ÔNIBUS EM MARROCOS'  (de 172.30.10.40:33042)
...
00:11:49 [Texto] Encerrando...
00:11:49 [Texto] Unbind(Texto) -> OK
```

(Os horários dos containers estão em UTC.)

### Local: `./demo_local.sh`

A saída é a mesma do Docker, com `127.0.0.1` no lugar dos IPs dos containers. Única diferença:
como a porta antiga fica fechada (conexão recusada), a falha aparece como `UNAVAILABLE`, enquanto
no Docker o IP do container parado deixa de responder e a chamada estoura o timeout
(`DEADLINE_EXCEEDED`):

```
[cliente] Calculadora.Add: 5 + 100 = 105   (atendido por 127.0.0.1:50051)
[cliente] ! Calculadora em 127.0.0.1:50051 não respondeu (UNAVAILABLE)
[cliente] ! refazendo Lookup, o endereço pode ter mudado (rebind)...
[cliente] Lookup('Calculadora') -> 127.0.0.1:50052
[cliente] Calculadora.Add: 6 + 100 = 106   (atendido por 127.0.0.1:50052)
[cliente] MIGRAÇÃO OBSERVADA: Calculadora passou de 127.0.0.1:50051 para 127.0.0.1:50052; o cliente continuou funcionando após novo Lookup.
```

Cliente com o serviço de nomes fora do ar:

```
[cliente] serviço de nomes: localhost:5678 | IP deste cliente: 127.0.0.1
[cliente] ! serviço de nomes em localhost:5678 não respondeu a Lookup (UNAVAILABLE)
```

## Limitações

- **Registro só em memória:** se o serviço de nomes reiniciar, todos os registros são perdidos e
  os serviços precisam ser reiniciados para fazer `Bind` de novo (não há re-registro automático
  nem heartbeat/lease).
- **Registros órfãos:** se um serviço morrer sem `SIGTERM` (ex.: `kill -9`, queda da máquina),
  o registro continua apontando para um endereço morto até alguém fazer `Rebind`/`Unbind`. O
  cliente avisa que o serviço está fora do ar.
- **Sem autenticação:** qualquer processo que alcance o serviço de nomes pode fazer `Bind`,
  `Rebind` ou `Unbind` de qualquer nome.
- **Canais inseguros:** tudo usa `insecure_channel`/`add_insecure_port` (sem TLS).
- **Unbind condicional não é atômico:** o servidor faz `Lookup` e depois `Unbind`; um `Rebind`
  feito entre as duas chamadas seria desfeito. Resolver isso exigiria um RPC novo (ex.: unbind
  condicionado ao endereço).
- **Ponto único de falha:** há uma só instância do serviço de nomes, sem replicação.
- O cliente refaz o `Lookup` só uma vez por chamada, como pedido. Se o serviço estiver
  reiniciando, a chamada falha com aviso e é preciso tentar de novo.
