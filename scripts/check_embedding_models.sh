#!/usr/bin/env bash
# Script para verificar quais modelos de embedding estão disponíveis
# em cada versão da API do Google Generative AI.
#
# Uso: GOOGLE_API_KEY=<sua-key> ./check_embedding_models.sh
#   ou: source .env && ./check_embedding_models.sh

set -euo pipefail

if [[ -z "${GOOGLE_API_KEY:-}" ]]; then
  echo "Erro: GOOGLE_API_KEY não definida."
  echo "Uso: GOOGLE_API_KEY=<key> $0"
  exit 1
fi

echo "=== API v1 — modelos de embedding ==="
curl -s "https://generativelanguage.googleapis.com/v1/models?key=${GOOGLE_API_KEY}" \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data.get('models', []):
    if 'embedding' in m['name'].lower() or 'embed' in ','.join(m.get('supportedGenerationMethods', [])):
        print(f\"  {m['name']}  methods={m.get('supportedGenerationMethods', [])}\")
" 2>/dev/null || echo "  (nenhum ou erro)"

echo ""
echo "=== API v1beta — modelos de embedding ==="
curl -s "https://generativelanguage.googleapis.com/v1beta/models?key=${GOOGLE_API_KEY}" \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data.get('models', []):
    if 'embedding' in m['name'].lower() or 'embed' in ','.join(m.get('supportedGenerationMethods', [])):
        print(f\"  {m['name']}  methods={m.get('supportedGenerationMethods', [])}\")
" 2>/dev/null || echo "  (nenhum ou erro)"

echo ""
echo "=== Teste direto: embedContent com text-embedding-004 ==="
for ver in v1 v1beta; do
  status=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "https://generativelanguage.googleapis.com/${ver}/models/text-embedding-004:embedContent?key=${GOOGLE_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"content":{"parts":[{"text":"teste"}]}}')
  echo "  ${ver}/text-embedding-004:embedContent → HTTP ${status}"
done

echo ""
echo "=== Teste direto: batchEmbedContents com text-embedding-004 ==="
for ver in v1 v1beta; do
  status=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST "https://generativelanguage.googleapis.com/${ver}/models/text-embedding-004:batchEmbedContents?key=${GOOGLE_API_KEY}" \
    -H "Content-Type: application/json" \
    -d '{"requests":[{"model":"models/text-embedding-004","content":{"parts":[{"text":"teste"}]}}]}')
  echo "  ${ver}/text-embedding-004:batchEmbedContents → HTTP ${status}"
done
