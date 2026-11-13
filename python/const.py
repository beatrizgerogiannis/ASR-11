import os

# Endereço padrão do serviço de nomes. Pode ser sobrescrito pelas variáveis de
# ambiente NS_HOST / NS_PORT (ou pelos argumentos --ns-host / --ns-porta dos programas).
# O original apontava para o IP da AWS do professor (34.203.80.210).
NS_IPADDR = os.environ.get('NS_HOST', 'localhost')
NS_PORT = os.environ.get('NS_PORT', '5678')
