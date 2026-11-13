#!/usr/bin/env bash
# Demonstração com Docker: cada papel num container com IP próprio (rede 172.30.10.0/24).
#   nomes 172.30.10.10 | calculadora .20 (migra para calculadora2 .21) | texto .30 | cliente .40
# Sobe tudo, roda o --demo do cliente, demonstra rebind (migração) e unbind, mostra os
# logs e derruba tudo. Uso: ./demo_docker.sh
set -euo pipefail
cd "$(dirname "$0")"
DC="docker compose"
trap '$DC --profile migracao --profile cliente down --remove-orphans >/dev/null 2>&1' EXIT

esperar_log() {  # esperar_log <serviço> <texto>
  for _ in $(seq 100); do $DC logs "$1" 2>/dev/null | grep -q "$2" && return; sleep 0.3; done
  echo "!! timeout esperando '$2' no log de $1"; return 1
}
secao() { echo; echo "################ $*"; }

secao "Construindo a imagem"
$DC build -q nomes

secao "Subindo serviço de nomes, Calculadora e Texto"
$DC up -d nomes calculadora texto
esperar_log calculadora "Bind("; esperar_log texto "Bind("

secao "Cliente --demo (container cliente, esperando a migração)"
$DC up -d --no-deps cliente
esperar_log cliente "=== 6."; sleep 2

secao "Rebind: nova instância da Calculadora em outro container/IP/porta (172.30.10.21:50052)"
$DC up -d --no-deps calculadora2
esperar_log calculadora2 "Rebind("; sleep 2

secao "IPs dos containers (todos no ar neste momento)"
for c in $($DC ps -aq); do
  docker inspect -f '{{.Name}} {{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$c"
done | sed 's#^/##' | sort -k2 -V | column -t

secao "Encerrando a Calculadora antiga (172.30.10.20)"
$DC stop calculadora
docker wait "$($DC ps -aq cliente)" >/dev/null

secao "Log do cliente (172.30.10.40)"
$DC logs --no-log-prefix cliente
$DC rm -fs cliente >/dev/null

secao "Unbind: encerrando o serviço Texto e tentando usá-lo"
$DC stop texto
$DC run --rm --no-deps -T cliente python cliente.py upper "ainda funciona?"

secao "testNS.py original, do container cliente para o serviço de nomes"
$DC run --rm --no-deps -T cliente python testNS.py

secao "Encerrando calculadora2 (Unbind)"
$DC stop calculadora2

for s in calculadora calculadora2 texto nomes; do
  secao "Log de $s"
  $DC logs --no-log-prefix "$s"
done
secao "Derrubando tudo"
