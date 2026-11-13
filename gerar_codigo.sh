#!/usr/bin/env bash
# Gera o código Python (mensagens + stubs gRPC) de todos os .proto em protos/
# e grava em python/. Uso: ./gerar_codigo.sh
set -euo pipefail
cd "$(dirname "$0")"

PY="${PYTHON:-python3}"
[ -x .venv/bin/python ] && PY=.venv/bin/python

for proto in protos/*.proto; do
  echo "Gerando código para $proto"
  "$PY" -m grpc_tools.protoc -Iprotos \
      --python_out=python --pyi_out=python --grpc_python_out=python "$proto"
done
