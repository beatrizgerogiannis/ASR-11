"""Cliente dos serviços Calculadora e Texto.

O cliente conhece apenas o endereço do serviço de nomes. Para cada serviço faz
Lookup pelo nome lógico, abre um canal no endereço devolvido e chama os RPCs.
Se a chamada falhar por indisponibilidade, refaz o Lookup uma vez (o serviço pode
ter migrado via Rebind) e tenta de novo.

Uso:
  python cliente.py --demo [--esperar-migracao SEG]   demonstração completa
  python cliente.py                                   modo interativo
  python cliente.py add 2 3                           um único comando
"""
import argparse
import shlex
import sys
import time

import grpc
import Calculadora_pb2
import Calculadora_pb2_grpc
import Texto_pb2
import Texto_pb2_grpc

from nomes_cliente import ClienteNomes, ServicoDeNomesIndisponivel, argumentos_ns, ip_local_para

TIMEOUT = 2  # segundos por chamada
STUBS = {
  'Calculadora': Calculadora_pb2_grpc.CalculadoraStub,
  'Texto': Texto_pb2_grpc.TextoStub,
}
REDE = (grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED)


def info(msg):
  print('[cliente] ' + msg, flush=True)


def aviso(msg):
  print('[cliente] ! ' + msg, flush=True)


class Cliente:

  def __init__(self, ns):
    self.ns = ns
    self._cache = {}  # servico -> (endereco, canal, stub)

  def lookup(self, servico):
    """Faz Lookup e devolve 'ip:porta' ou None (avisando o motivo)."""
    try:
      end = self.ns.lookup(servico)
    except ServicoDeNomesIndisponivel as e:
      aviso(str(e))
      return None
    if end is None:
      aviso("Lookup('%s'): serviço não registrado no serviço de nomes" % servico)
      return None
    endereco = '%s:%s' % end
    info("Lookup('%s') -> %s" % (servico, endereco))
    return endereco

  def _stub(self, servico, novo_lookup=False):
    if servico in self._cache and not novo_lookup:
      return self._cache[servico]
    antigo = self._cache.pop(servico, None)
    if antigo:
      antigo[1].close()
    endereco = self.lookup(servico)
    if endereco is None:
      return None
    canal = grpc.insecure_channel(endereco)
    self._cache[servico] = (endereco, canal, STUBS[servico](canal))
    return self._cache[servico]

  def chamar(self, servico, rpc, req):
    """Chama servico.rpc(req). Devolve a resposta ou None (já avisando o erro)."""
    for tentativa in (1, 2):
      entrada = self._stub(servico, novo_lookup=(tentativa == 2))
      if entrada is None:
        return None
      endereco, _, stub = entrada
      try:
        return getattr(stub, rpc)(req, timeout=TIMEOUT)
      except grpc.RpcError as e:
        if e.code() not in REDE:
          aviso('%s.%s recusado pelo servidor: %s: %s' % (servico, rpc, e.code().name, e.details()))
          return None
        aviso('%s em %s não respondeu (%s)' % (servico, endereco, e.code().name))
        if tentativa == 1:
          aviso('refazendo Lookup, o endereço pode ter mudado (rebind)...')
    aviso('%s está fora do ar. Tente novamente mais tarde.' % servico)
    return None

  # --- operações de alto nível -------------------------------------------------

  def calc(self, op, a, b):
    r = self.chamar('Calculadora', op, Calculadora_pb2.OperandosMsg(a=a, b=b))
    if r:
      info('Calculadora.%s: %s   (atendido por %s)' % (op, r.expressao, r.servidor))
    return r

  def texto(self, op, t):
    r = self.chamar('Texto', op, Texto_pb2.TextoMsg(texto=t))
    if r is None:
      return None
    if op == 'CountWords':
      info('Texto.CountWords(%r) -> %d palavras' % (t, r.palavras))
    elif op == 'Analyze':
      info('Texto.Analyze(%r)   (atendido por %s)' % (t, r.servidor))
      for campo in ('caracteres', 'palavras', 'linhas', 'vogais', 'tamanho_medio_palavra',
                    'palavra_mais_longa', 'palindromo'):
        print('            %-22s %s' % (campo, getattr(r, campo)))
      print('            %-22s %s' % ('mais_frequentes',
            ', '.join('%s(%d)' % (f.palavra, f.ocorrencias) for f in r.mais_frequentes)))
    else:
      info('Texto.%s(%r) -> %r' % (op, t, r.texto))
    return r


def titulo(s):
  print('\n=== %s ===' % s, flush=True)


def demo(cli, esperar_migracao):
  titulo('1. Lookup dos serviços')
  cli._stub('Calculadora')
  cli._stub('Texto')

  titulo('2. Calculadora')
  cli.calc('Add', 7, 5)
  cli.calc('Sub', 7, 5)
  cli.calc('Mul', 7, 5)
  cli.calc('Div', 7, 2)

  titulo('3. Erro: divisão por zero (INVALID_ARGUMENT)')
  cli.calc('Div', 7, 0)

  titulo('4. Texto')
  frase = 'Socorram-me, subi no ônibus em Marrocos'
  cli.texto('Upper', frase)
  cli.texto('Reverse', frase)
  cli.texto('CountWords', frase)
  cli.texto('Analyze', 'o rato roeu a roupa do rei de Roma\ne o rei roeu o resto')
  cli.texto('Analyze', frase)

  titulo('5. Lookup de um serviço que não existe')
  cli.lookup('Impressora')

  if esperar_migracao:
    titulo('6. Migração: aguardando a Calculadora mudar de endereço (até %ds)' % esperar_migracao)
    entrada = cli._cache.get('Calculadora')
    inicial = entrada[0] if entrada else None
    info('endereço atual em cache: %s' % inicial)
    fim = time.time() + esperar_migracao
    i = 0
    while time.time() < fim:
      i += 1
      r = cli.calc('Add', i, 100)
      if r and inicial and r.servidor != inicial:
        info('MIGRAÇÃO OBSERVADA: Calculadora passou de %s para %s; '
             'o cliente continuou funcionando após novo Lookup.' % (inicial, r.servidor))
        break
      time.sleep(1)
    else:
      aviso('nenhuma migração observada em %ds' % esperar_migracao)


AJUDA = """Comandos:
  add|sub|mul|div A B                    Calculadora
  upper|reverse|count|analyze TEXTO      Texto
  lookup NOME                            consulta o serviço de nomes
  ajuda | sair"""

OPS_CALC = {'add': 'Add', 'sub': 'Sub', 'mul': 'Mul', 'div': 'Div'}
OPS_TEXTO = {'upper': 'Upper', 'reverse': 'Reverse', 'count': 'CountWords', 'analyze': 'Analyze'}


def executar_comando(cli, partes):
  if not partes:
    return True
  cmd, resto = partes[0].lower(), partes[1:]
  if cmd in ('sair', 'exit', 'quit'):
    return False
  if cmd in OPS_CALC:
    try:
      a, b = (float(x) for x in resto)
    except ValueError:
      aviso('uso: %s A B (dois números)' % cmd)
      return True
    cli.calc(OPS_CALC[cmd], a, b)
  elif cmd in OPS_TEXTO:
    cli.texto(OPS_TEXTO[cmd], ' '.join(resto))
  elif cmd == 'lookup' and len(resto) == 1:
    cli.lookup(resto[0])
  else:
    print(AJUDA)
  return True


def interativo(cli):
  print(AJUDA)
  while True:
    try:
      linha = input('> ')
    except EOFError:
      break
    try:
      partes = shlex.split(linha)
    except ValueError as e:
      aviso(str(e))
      continue
    if not executar_comando(cli, partes):
      break


def main():
  p = argparse.ArgumentParser(description='Cliente dos serviços Calculadora e Texto')
  argumentos_ns(p)
  p.add_argument('--demo', action='store_true', help='executa a demonstração completa')
  p.add_argument('--esperar-migracao', type=int, default=0, metavar='SEG',
                 help='no --demo, espera até SEG segundos a Calculadora migrar (rebind)')
  p.add_argument('comando', nargs='*', help='comando único (ex.: add 2 3); sem nada: interativo')
  args = p.parse_args()

  ns = ClienteNomes(args.ns_host, args.ns_porta)
  info('serviço de nomes: %s | IP deste cliente: %s'
       % (ns.endereco, ip_local_para(args.ns_host, args.ns_porta)))
  cli = Cliente(ns)
  try:
    if args.demo:
      demo(cli, args.esperar_migracao)
    elif args.comando:
      executar_comando(cli, args.comando)
    else:
      interativo(cli)
  except KeyboardInterrupt:
    pass
  return 0


if __name__ == '__main__':
  sys.exit(main())
