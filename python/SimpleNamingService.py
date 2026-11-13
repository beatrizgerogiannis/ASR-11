"""Serviço de nomes (evolução do SimpleNamingService do prof. Fábio).

A interface (.proto) é a mesma do original; mudou só a implementação:
  * registro em dict {nome: (ip, porta)} protegido por threading.Lock
    (o servidor atende até 10 requisições em paralelo);
  * Bind de nome já existente é recusado (use Rebind);
  * Rebind de nome inexistente é recusado (antes: IndexError);
  * Lookup de nome inexistente devolve endereço vazio (compatível com o original);
  * log de cada operação; porta configurável por argumento/variável de ambiente.

Status devolvido: "OK" em caso de sucesso, "NOK: <motivo>" em caso de erro.
"""
from concurrent import futures
import argparse
import logging
import signal
import threading
from urllib.parse import unquote

import grpc
import SimpleNamingService_pb2
import SimpleNamingService_pb2_grpc

import const

log = logging.getLogger('Nomes')


def _peer(context):
  # context.peer() vem como "ipv4:172.30.10.20:41234" ou "ipv6:[::1]:41234"
  return unquote(context.peer()).split(':', 1)[-1]


class SimpleNamingServer(SimpleNamingService_pb2_grpc.SimpleNamingServiceServicer):

  def __init__(self):
    self._db = {}                   # nome -> (ip, porta)
    self._lock = threading.Lock()

  def _status(self, op, nome, endereco, status, context, nota=''):
    log.info('%-6s nome=%-12s endereco=%-21s -> %s%s (de %s)',
             op, repr(nome), endereco, status, nota, _peer(context))
    return SimpleNamingService_pb2.StatusMsg(status=status)

  @staticmethod
  def _validar(request):
    if not request.name:
      return 'NOK: nome vazio'
    if not request.address.ipaddress or not request.address.portnumber:
      return 'NOK: endereço incompleto (ipaddress e portnumber são obrigatórios)'
    return None

  def Bind(self, request, context):
    nome = request.name
    end = (request.address.ipaddress, request.address.portnumber)
    erro = self._validar(request)
    if erro is None:
      with self._lock:
        if nome in self._db:
          atual = self._db[nome]
          erro = "NOK: nome já registrado em %s:%s; use Rebind" % atual
        else:
          self._db[nome] = end
    return self._status('Bind', nome, '%s:%s' % end, erro or 'OK', context)

  def Lookup(self, request, context):
    with self._lock:
      end = self._db.get(request.name)
    if end is None:
      # Mantido como no original (endereço vazio) para não quebrar clientes antigos,
      # como o testNS.py. Não usamos context.set_code(NOT_FOUND) porque isso faria
      # o stub do cliente levantar exceção.
      log.info('%-6s nome=%-12s -> não encontrado, devolve endereço vazio (de %s)',
               'Lookup', repr(request.name), _peer(context))
      return SimpleNamingService_pb2.AddressMsg(ipaddress='', portnumber='')
    log.info('%-6s nome=%-12s -> %s:%s (de %s)',
             'Lookup', repr(request.name), end[0], end[1], _peer(context))
    return SimpleNamingService_pb2.AddressMsg(ipaddress=end[0], portnumber=end[1])

  def Rebind(self, request, context):
    nome = request.name
    end = (request.address.ipaddress, request.address.portnumber)
    antigo = None
    erro = self._validar(request)
    if erro is None:
      with self._lock:
        if nome not in self._db:
          erro = 'NOK: nome não registrado; use Bind'
        else:
          antigo = self._db[nome]
          self._db[nome] = end
    nota = ' [antes: %s:%s]' % antigo if antigo else ''
    return self._status('Rebind', nome, '%s:%s' % end, erro or 'OK', context, nota)

  def Unbind(self, request, context):
    nome = request.name
    with self._lock:
      end = self._db.pop(nome, None)
    if end is None:
      return self._status('Unbind', nome, '-', 'NOK: nome não registrado', context)
    return self._status('Unbind', nome, '%s:%s' % end, 'OK', context)


def serve(porta):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    SimpleNamingService_pb2_grpc.add_SimpleNamingServiceServicer_to_server(
      SimpleNamingServer(), server)
    server.add_insecure_port('[::]:' + str(porta))
    server.start()
    log.info('Serviço de nomes ouvindo na porta %s', porta)

    parar = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: parar.set())
    signal.signal(signal.SIGINT, lambda *_: parar.set())
    parar.wait()
    log.info('Encerrando serviço de nomes (registros em memória serão perdidos)')
    server.stop(grace=1).wait()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Serviço de nomes gRPC')
    p.add_argument('--porta', default=const.NS_PORT,
                   help='porta de escuta (padrão: $NS_PORT ou const.NS_PORT = %(default)s)')
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s',
                        datefmt='%H:%M:%S')
    serve(args.porta)
