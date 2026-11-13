#!/usr/bin/env bash
# Demonstração local: serviço de nomes, Calculadora, Texto e cliente como processos
# separados (em background), na mesma máquina. Logs em logs/*.log.
# Uso: ./demo_local.sh
set -uo pipefail
cd "$(dirname "$0")"
PY="$PWD/.venv/bin/python"; [ -x "$PY" ] || PY=python3
export PYTHONUNBUFFERED=1 NS_HOST=localhost NS_PORT=5678
LOGS="$PWD/logs"; mkdir -p "$LOGS"; rm -f "$LOGS"/*.log
cd python

PIDS=()
iniciar() {  # iniciar <log> <comando...>
  local log=$1; shift
  "$PY" "$@" > "$LOGS/$log.log" 2>&1 &
  PIDS+=($!); echo ">> iniciado $log (pid $!): $*"
}
encerrar_tudo() {  # em ordem inversa: serviços fazem Unbind antes de o serviço de nomes sair
  for ((i=${#PIDS[@]}-1; i>=0; i--)); do
    kill "${PIDS[i]}" 2>/dev/null && wait "${PIDS[i]}" 2>/dev/null
  done
}
trap encerrar_tudo EXIT
esperar_log() {  # esperar_log <log> <texto>
  for _ in $(seq 50); do grep -q "$2" "$LOGS/$1.log" 2>/dev/null && return; sleep 0.2; done
  echo "!! timeout esperando '$2' em $1.log"
}

iniciar nomes SimpleNamingService.py
esperar_log nomes "ouvindo"
iniciar calculadora CalculadoraService.py --porta 50051 --anunciar 127.0.0.1
iniciar texto TextoService.py --porta 50061 --anunciar 127.0.0.1
esperar_log calculadora "Bind"; esperar_log texto "Bind"

echo ">> cliente --demo (em background, esperando a migração)"
iniciar cliente cliente.py --demo --esperar-migracao 30
CLIENTE=${PIDS[-1]}
esperar_log cliente "=== 6."; sleep 2

echo ">> migração: nova Calculadora na porta 50052 (Bind falha -> Rebind)"
iniciar calculadora2 CalculadoraService.py --porta 50052 --anunciar 127.0.0.1
esperar_log calculadora2 "Rebind"; sleep 2
echo ">> encerrando a Calculadora antiga (porta 50051)"
kill "${PIDS[1]}"
wait "$CLIENTE"

echo ">> unbind: encerrando o serviço Texto (SIGTERM)"
kill "${PIDS[2]}"; esperar_log texto "Unbind("; sleep 0.5
"$PY" cliente.py upper "ainda funciona?" > "$LOGS/cliente_apos_unbind.log" 2>&1
echo ">> testNS.py original contra o mesmo serviço de nomes"
"$PY" testNS.py > "$LOGS/testNS.log" 2>&1
"$PY" testErrosNS.py > "$LOGS/testErrosNS.log" 2>&1

encerrar_tudo; trap - EXIT
for f in nomes calculadora calculadora2 texto cliente cliente_apos_unbind testNS testErrosNS; do
  echo; echo "################ logs/$f.log"; cat "$LOGS/$f.log"
done
