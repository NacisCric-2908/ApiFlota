#!/usr/bin/env bash
# Enciende o apaga el «siempre encendido» de los servicios de Flota.
#
#   encendido  1 réplica siempre activa: responde de inmediato. Úselo unas horas antes de la demostración.
#   ahorro     escala a cero: no cuesta en reposo, pero la PRIMERA petición tras un rato sin uso tarda varios segundos
#              (y puede dar error porque el gateway y el MID esperan poco). Es el modo normal.
#
# Los siguientes despliegues del CD conservan el valor que deje aquí.
set -euo pipefail
GRUPO="${GRUPO:-rg-rodar}"
case "${1:-}" in
  encendido) MIN=1 ;;
  ahorro) MIN=0 ;;
  *) echo "Uso: $0 encendido|ahorro" >&2; exit 1 ;;
esac
az extension add --name containerapp --upgrade --yes --only-show-errors >/dev/null 2>&1 || true
for app in rodar-gateway rodar-tokens flota-crud flota-mid; do
  if az containerapp show --name "$app" --resource-group "$GRUPO" --output none 2>/dev/null; then
    az containerapp update --name "$app" --resource-group "$GRUPO" --min-replicas "$MIN" --output none
    echo "$app: mínimo de réplicas = $MIN"
  else
    echo "$app: no existe todavía (se omite)"
  fi
done
