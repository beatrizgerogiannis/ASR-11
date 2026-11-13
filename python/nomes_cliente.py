"""Funções auxiliares para falar com o serviço de nomes.

Usado pelos servidores de aplicação (registrar/desregistrar) e pelo cliente (lookup).
"""
from concurrent import futures
import argparse
import logging
import os
import signal
import socket
import threading
from urllib.parse import unquote

import grpc
import SimpleNamingService_pb2 as ns_pb2
import SimpleNamingService_pb2_grpc as ns_grpc

import const

TIMEOUT_NS = 3  # segundos


class ServicoDeNomesIndisponivel(Exception):
  pass


class ClienteNomes:
  """Stub do serviço de nomes com tratamento de erro de rede."""

  def __init__(self, host, porta):
    self.endereco = '%s:%s' % (host, porta)
    self._canal = grpc.insecure_channel(self.endereco)
    self._stub = ns_grpc.SimpleNamingServiceStub(self._canal)

  def _chamar(self, metodo, req):
    try:
      return getattr(self._stub, metodo)(req, timeout=TIMEOUT_NS)
    except grpc.RpcError as e:
      raise ServicoDeNomesIndisponivel(
        'serviço de nomes em %s não respondeu a %s (%s)' % (self.endereco, metodo, e.code().name))

  def lookup(self, nome):
    """Devolve (ip, porta) ou None se o nome não estiver registrado."""
    r = self._chamar('Lookup', ns_pb2.NameMsg(name=nome))
    if not r.ipaddress:          # o serviço devolve endereço vazio quando não acha
      return None
    return r.ipaddress, r.portnumber

  def bind(self, nome, ip, porta):
    return self._chamar('Bind', ns_pb2.BindMsg(
      name=nome, address=ns_pb2.AddressMsg(ipaddress=ip, portnumber=str(porta)))).status

  def rebind(self, nome, ip, porta):
    return self._chamar('Rebind', ns_pb2.BindMsg(
      name=nome, address=ns_pb2.AddressMsg(ipaddress=ip, portnumber=str(porta)))).status

  def unbind(self, nome):
    return self._chamar('Unbind', ns_pb2.NameMsg(name=nome)).status

  def close(self):
    self._canal.close()


def peer(context):
  """Endereço de quem fez a chamada, ex.: '172.30.10.40:51234'."""
  return unquote(context.peer()).split(':', 1)[-1]


def argumentos_ns(parser):
  """Acrescenta --ns-host/--ns-porta (padrão: variáveis de ambiente ou const.py)."""
  parser.add_argument('--ns-host', default=const.NS_IPADDR,
                      help='endereço do serviço de nomes (padrão: $NS_HOST ou %(default)s)')
  parser.add_argument('--ns-porta', default=const.NS_PORT,
                      help='porta do serviço de nomes (padrão: $NS_PORT ou %(default)s)')


def ip_local_para(host, porta):
  """IP desta máquina na interface usada para alcançar `host` (só consulta a rota,
  não envia pacotes). Serve de padrão para o IP anunciado no Bind."""
  try:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
      s.connect((socket.gethostbyname(host), int(porta)))
      return s.getsockname()[0]
  except OSError:
    return '127.0.0.1'


def executar_servidor(nome_padrao, porta_padrao, registrar_servicer, descricao):
  """Ciclo de vida comum aos servidores de aplicação:
  sobe o gRPC, faz Bind (ou Rebind se o nome já existir), espera Ctrl+C/SIGTERM,
  faz Unbind (só se o registro ainda apontar para este processo) e encerra."""
  p = argparse.ArgumentParser(description=descricao)
  p.add_argument('--nome', default=os.environ.get('NOME_SERVICO', nome_padrao),
                 help='nome lógico registrado no serviço de nomes (padrão: %(default)s)')
  p.add_argument('--porta', default=os.environ.get('PORTA', porta_padrao),
                 help='porta de escuta (padrão: $PORTA ou %(default)s)')
  p.add_argument('--anunciar', default=os.environ.get('ANUNCIAR_IP'),
                 help='IP anunciado no Bind (padrão: $ANUNCIAR_IP ou o IP local usado '
                      'para alcançar o serviço de nomes). Não use 0.0.0.0.')
  argumentos_ns(p)
  args = p.parse_args()

  logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(message)s',
                      datefmt='%H:%M:%S')
  log = logging.getLogger(args.nome)

  ip = args.anunciar or ip_local_para(args.ns_host, args.ns_porta)
  porta = str(args.porta)
  meu_endereco = '%s:%s' % (ip, porta)

  server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
  registrar_servicer(server, meu_endereco)
  server.add_insecure_port('[::]:' + porta)
  server.start()
  log.info('Servidor ouvindo em [::]:%s, anunciando %s', porta, meu_endereco)

  ns = ClienteNomes(args.ns_host, args.ns_porta)
  try:
    status = ns.bind(args.nome, ip, porta)
    log.info('Bind(%s, %s) no serviço de nomes %s -> %s', args.nome, meu_endereco, ns.endereco, status)
    if status != 'OK':
      status = ns.rebind(args.nome, ip, porta)
      log.info('Rebind(%s, %s) -> %s', args.nome, meu_endereco, status)
      if status != 'OK':
        raise ServicoDeNomesIndisponivel('não foi possível registrar: ' + status)
  except ServicoDeNomesIndisponivel as e:
    log.error('%s. Encerrando.', e)
    server.stop(0)
    raise SystemExit(1)

  parar = threading.Event()
  signal.signal(signal.SIGTERM, lambda *_: parar.set())
  signal.signal(signal.SIGINT, lambda *_: parar.set())
  parar.wait()

  log.info('Encerrando...')
  try:
    # Se outra instância fez Rebind (migração), o nome não é mais nosso: não remove.
    atual = ns.lookup(args.nome)
    if atual == (ip, porta):
      log.info('Unbind(%s) -> %s', args.nome, ns.unbind(args.nome))
    else:
      log.info('Unbind não feito: %s agora aponta para %s (outra instância)',
               args.nome, '%s:%s' % atual if atual else 'nada')
  except ServicoDeNomesIndisponivel as e:
    log.warning('%s; registro não removido', e)
  server.stop(grace=1).wait()
  ns.close()
