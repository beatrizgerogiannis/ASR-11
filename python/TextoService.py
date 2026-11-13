"""Serviço 2: processamento de Texto (Upper, Reverse, CountWords, Analyze) em gRPC.

Ao iniciar faz Bind no serviço de nomes como "Texto" (ou Rebind, se o nome já
existir) e, ao receber Ctrl+C/SIGTERM, faz Unbind.
Exemplo: python TextoService.py --porta 50061 --anunciar 127.0.0.1
"""
from collections import Counter
import logging
import re
import unicodedata

import Texto_pb2
import Texto_pb2_grpc

from nomes_cliente import executar_servidor, peer

VOGAIS = set('aeiou')


def _sem_acento(s):
  return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def _palavras(texto):
  return re.findall(r'\w+', texto.lower())


class TextoServer(Texto_pb2_grpc.TextoServicer):

  def __init__(self, endereco):
    self.endereco = endereco
    self.log = logging.getLogger('Texto')

  def _log(self, op, texto, resultado, context):
    self.log.info('%s(%r) -> %s  (de %s)', op, texto, resultado, peer(context))

  def Upper(self, request, context):
    r = request.texto.upper()
    self._log('Upper', request.texto, repr(r), context)
    return Texto_pb2.TextoMsg(texto=r)

  def Reverse(self, request, context):
    r = request.texto[::-1]
    self._log('Reverse', request.texto, repr(r), context)
    return Texto_pb2.TextoMsg(texto=r)

  def CountWords(self, request, context):
    n = len(_palavras(request.texto))
    self._log('CountWords', request.texto, n, context)
    return Texto_pb2.ContagemMsg(palavras=n)

  def Analyze(self, request, context):
    t = request.texto
    pals = _palavras(t)
    letras = [c for c in _sem_acento(t).lower() if c.isalnum()]
    resp = Texto_pb2.AnaliseMsg(
      caracteres=len(t),
      palavras=len(pals),
      linhas=len(t.splitlines()) if t else 0,
      vogais=sum(1 for c in letras if c in VOGAIS),
      tamanho_medio_palavra=round(sum(map(len, pals)) / len(pals), 2) if pals else 0.0,
      palavra_mais_longa=max(pals, key=len) if pals else '',
      palindromo=bool(letras) and letras == letras[::-1],
      servidor=self.endereco,
    )
    for palavra, n in Counter(pals).most_common(5):
      resp.mais_frequentes.add(palavra=palavra, ocorrencias=n)
    self._log('Analyze', t, '%d palavras' % resp.palavras, context)
    return resp


if __name__ == '__main__':
  executar_servidor(
    'Texto', '50061',
    lambda server, end: Texto_pb2_grpc.add_TextoServicer_to_server(TextoServer(end), server),
    'Serviço gRPC de processamento de texto')
