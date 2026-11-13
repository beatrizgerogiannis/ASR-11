"""Testa os casos de erro do serviço de nomes (que no código original falhavam).
Uso: python testErrosNS.py   (serviço de nomes em $NS_HOST:$NS_PORT, padrão localhost:5678)"""
import grpc
import SimpleNamingService_pb2 as pb
import SimpleNamingService_pb2_grpc as pb_grpc

import const


def end(ip, porta):
  return pb.AddressMsg(ipaddress=ip, portnumber=porta)


with grpc.insecure_channel(const.NS_IPADDR + ':' + const.NS_PORT) as canal:
  ns = pb_grpc.SimpleNamingServiceStub(canal)
  print('Bind X 10.0.0.1:1           ->', ns.Bind(pb.BindMsg(name='X', address=end('10.0.0.1', '1'))).status)
  print('Bind X 10.0.0.2:2 (repetido) ->', ns.Bind(pb.BindMsg(name='X', address=end('10.0.0.2', '2'))).status)
  print('Rebind X 10.0.0.2:2         ->', ns.Rebind(pb.BindMsg(name='X', address=end('10.0.0.2', '2'))).status)
  r = ns.Lookup(pb.NameMsg(name='X'))
  print('Lookup X                    ->', r.ipaddress + ':' + r.portnumber)
  print('Unbind X                    ->', ns.Unbind(pb.NameMsg(name='X')).status)
  r = ns.Lookup(pb.NameMsg(name='X'))
  print('Lookup X (após unbind)      -> %r:%r (vazio = não encontrado)' % (r.ipaddress, r.portnumber))
  print('Unbind X (de novo)          ->', ns.Unbind(pb.NameMsg(name='X')).status)
  print('Rebind NaoExiste            ->', ns.Rebind(pb.BindMsg(name='NaoExiste', address=end('1.1.1.1', '1'))).status)
  print('Bind Y sem endereço         ->', ns.Bind(pb.BindMsg(name='Y')).status)
