#!/usr/bin/env bash
# Crea el grupo de recursos y despliega la plataforma compartida (ACR, logs, entorno de Container Apps y Cosmos DB).
# Se ejecuta UNA vez, desde su computador, con la CLI de Azure ya autenticada (`az login`).
#
#   infra/scripts/01-plataforma.sh                         pide confirmación
#   CONFIRMAR=si infra/scripts/01-plataforma.sh            sin preguntar
#   GRUPO=rg-rodar UBICACION=eastus PREFIJO=rodar ...      cambia los valores por defecto
set -euo pipefail

GRUPO="${GRUPO:-rg-rodar}"
UBICACION="${UBICACION:-eastus}"
PREFIJO="${PREFIJO:-rodar}"
COSMOS_EXISTENTE="${COSMOS_EXISTENTE:-}"
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"

command -v az >/dev/null || { echo "Instale la CLI de Azure (https://aka.ms/installazurecli) y ejecute 'az login'." >&2; exit 1; }
az account show >/dev/null 2>&1 || { echo "No hay sesión de Azure: ejecute primero 'az login'." >&2; exit 1; }

echo "Suscripción: $(az account show --query name -o tsv)"
echo "Grupo de recursos: $GRUPO ($UBICACION), prefijo: $PREFIJO"
echo "Crea: ACR Basic (~\$5/mes), logs con tope diario, entorno de Container Apps y Cosmos DB serverless."
if [[ "${CONFIRMAR:-}" != "si" ]]; then
  read -r -p "¿Continuar? [s/N] " respuesta
  [[ "$respuesta" == [sS] ]] || { echo "Cancelado."; exit 0; }
fi

az group create --name "$GRUPO" --location "$UBICACION" --output none
az deployment group create \
  --resource-group "$GRUPO" \
  --template-file "$RAIZ/plataforma.bicep" \
  --parameters prefijo="$PREFIJO" ubicacion="$UBICACION" cosmosExistente="$COSMOS_EXISTENTE" \
  --query properties.outputs --output json

echo
echo "Listo. Siguiente paso: infra/scripts/02-acceso-github.sh"
