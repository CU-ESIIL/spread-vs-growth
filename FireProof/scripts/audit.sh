#!/usr/bin/env bash
set -euo pipefail

if rg -n '^\s*(sorry|admit)\b' FireProof FireProof.lean AxiomAudit.lean; then
  echo "Unresolved proof placeholder found." >&2
  exit 1
fi

lake build
lake env lean AxiomAudit.lean
