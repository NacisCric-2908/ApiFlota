#!/usr/bin/env bash
# Deja que GitHub Actions despliegue en Azure SIN guardar ninguna contraseña: autenticación federada (OIDC).
# Crea (o reutiliza) un registro de aplicación en Microsoft Entra ID, le da el rol Contributor sobre el grupo de recursos,
# le agrega una credencial federada por repositorio (solo para la rama main) y guarda en cada repositorio las variables
# AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_SUBSCRIPTION_ID y AZURE_RESOURCE_GROUP.
#
# Requisitos: `az login` y `gh auth login` hechos, y permiso para registrar aplicaciones en su tenant de Entra ID
# (si su universidad lo bloquea, vea la sección «Si no puede registrar aplicaciones» de docs/despliegue-azure.md).
#
#   DUENO=su-usuario-de-github infra/scripts/02-acceso-github.sh
#   REPOS="ApiFlota ApiFlotaMID ApiWategay" GRUPO=rg-rodar DUENO=... infra/scripts/02-acceso-github.sh
set -euo pipefail

: "${DUENO:?Defina DUENO con su usuario u organización de GitHub, p. ej. DUENO=NacisCric-2908}"
GRUPO="${GRUPO:-rg-rodar}"
REPOS="${REPOS:-ApiFlota ApiFlotaMID ApiWategay}"
NOMBRE_APP="${NOMBRE_APP:-github-despliegue-rodar}"

command -v az >/dev/null || { echo "Falta la CLI de Azure (az)." >&2; exit 1; }
command -v gh >/dev/null || { echo "Falta la CLI de GitHub (gh): https://cli.github.com y 'gh auth login'." >&2; exit 1; }
az account show >/dev/null 2>&1 || { echo "Ejecute primero 'az login'." >&2; exit 1; }

SUSCRIPCION="$(az account show --query id -o tsv)"
TENANT="$(az account show --query tenantId -o tsv)"
ALCANCE="/subscriptions/$SUSCRIPCION/resourceGroups/$GRUPO"
az group show --name "$GRUPO" --output none || { echo "No existe el grupo '$GRUPO': ejecute antes 01-plataforma.sh." >&2; exit 1; }

APP_ID="$(az ad app list --display-name "$NOMBRE_APP" --query "[0].appId" -o tsv)"
if [[ -z "$APP_ID" ]]; then
  APP_ID="$(az ad app create --display-name "$NOMBRE_APP" --query appId -o tsv)" || {
    echo "No se pudo registrar la aplicación (¿su tenant lo bloquea?). Vea docs/despliegue-azure.md." >&2; exit 1; }
fi
az ad sp show --id "$APP_ID" >/dev/null 2>&1 || az ad sp create --id "$APP_ID" --output none

# El principal de servicio recién creado tarda unos segundos en propagarse: se reintenta.
for intento in 1 2 3 4 5; do
  if az role assignment create --assignee "$APP_ID" --assignee-principal-type ServicePrincipal \
       --role Contributor --scope "$ALCANCE" --output none 2>/dev/null; then break; fi
  [[ "$intento" == 5 ]] && { echo "No se pudo asignar el rol Contributor sobre $GRUPO." >&2; exit 1; }
  sleep 10
done

for repo in $REPOS; do
  credencial="main-$repo"
  existe="$(az ad app federated-credential list --id "$APP_ID" --query "[?name=='$credencial'].name" -o tsv)"
  if [[ -z "$existe" ]]; then
    az ad app federated-credential create --id "$APP_ID" --parameters "{
      \"name\": \"$credencial\",
      \"issuer\": \"https://token.actions.githubusercontent.com\",
      \"subject\": \"repo:$DUENO/$repo:ref:refs/heads/main\",
      \"audiences\": [\"api://AzureADTokenExchange\"]}" --output none
  fi
  gh variable set AZURE_CLIENT_ID --repo "$DUENO/$repo" --body "$APP_ID"
  gh variable set AZURE_TENANT_ID --repo "$DUENO/$repo" --body "$TENANT"
  gh variable set AZURE_SUBSCRIPTION_ID --repo "$DUENO/$repo" --body "$SUSCRIPCION"
  gh variable set AZURE_RESOURCE_GROUP --repo "$DUENO/$repo" --body "$GRUPO"
  echo "$DUENO/$repo: credencial federada y variables listas"
done

echo
echo "Listo. Siguiente paso: configurar los secretos (en el repositorio del gateway: scripts/03-secretos-produccion.sh)."
