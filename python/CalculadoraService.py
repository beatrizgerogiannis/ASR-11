"""Serviço 1: Calculadora (Add, Sub, Mul, Div) em gRPC.

Ao iniciar faz Bind no serviço de nomes como "Calculadora" (ou Rebind, se o nome já
existir) e, ao receber Ctrl+C/SIGTERM, faz Unbind.
Exemplo: python CalculadoraService.py --porta 50051 --anunciar 127.0.0.1
"""
import logging

import grpc
import Calculadora_pb2
import Calculadora_pb2_grpc

from nomes_cliente import executar_servidor, peer


def _fmt(x):
  return ('%g' % x)


class CalculadoraServer(Calculadora_pb2_grpc.CalculadoraServicer):

  def __init__(self, endereco):
    self.endereco = endereco
    self.log = logging.getLogger('Calculadora')

  def _resp(self, op, req, valor, context):
    expr = '%s %s %s = %s' % (_fmt(req.a), op, _fmt(req.b), _fmt(valor))
    self.log.info('%s  (de %s)', expr, peer(context))
    return Calculadora_pb2.ResultadoMsg(valor=valor, expressao=expr, servidor=self.endereco)

  def Add(self, request, context):
    return self._resp('+', request, request.a + request.b, context)

  def Sub(self, request, context):
    return self._resp('-', request, request.a - request.b, context)

  def Mul(self, request, context):
    return self._resp('*', request, request.a * request.b, context)

  def Div(self, request, context):
    if request.b == 0:
      self.log.info('%s / 0 -> INVALID_ARGUMENT  (de %s)', _fmt(request.a),
                    peer(context))
      context.abort(grpc.StatusCode.INVALID_ARGUMENT, 'divisão por zero')
    return self._resp('/', request, request.a / request.b, context)


if __name__ == '__main__':
  executar_servidor(
    'Calculadora', '50051',
    lambda server, end: Calculadora_pb2_grpc.add_CalculadoraServicer_to_server(
      CalculadoraServer(end), server),
    'Serviço gRPC de calculadora')
