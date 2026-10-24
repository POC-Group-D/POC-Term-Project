#!/usr/bin/env bash
# Regenerate the gRPC stubs from the shared Online Boutique proto, so v2
# always exposes exactly the same API as v1.
# Requires grpcio-tools (pip install -r requirements-dev.txt).
set -euo pipefail

cd "$(dirname "$0")"
out=recommendation_agent/proto

python -m grpc_tools.protoc \
  -I ../online-boutique/protos \
  --python_out="$out" \
  --grpc_python_out="$out" \
  ../online-boutique/protos/demo.proto

# protoc emits an absolute import; make it relative to the package.
sed -i 's/^import demo_pb2 as/from . import demo_pb2 as/' "$out/demo_pb2_grpc.py"
