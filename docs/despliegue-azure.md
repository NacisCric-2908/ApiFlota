# Despliegue en Azure

Cómo llevar a Azure los **cuatro servicios de Flota** (CRUD, MID, servicio de tokens y gateway). Esta guía es la principal: los repositorios `ApiFlotaMID` y `ApiWategay` tienen la suya y apuntan aquí para la parte compartida.

> **Estado.** Todo el código de despliegue está escrito y se validó con las herramientas de línea de comandos (ver [«Qué se verificó»](#qué-se-verificó-y-qué-no)). **No se ha desplegado nunca en una suscripción real**: la primera vez puede pedir un ajuste menor, y los puntos más probables están marcados en [«Si algo falla»](#si-algo-falla).

## 1. Qué se crea

```
GitHub (3 repositorios)                        Azure (un grupo de recursos: rg-rodar)
┌────────────────────┐   push a main           ┌──────────────────────────────────────────────┐
│ ApiFlota           │ ──── CD (OIDC) ───────► │ ACR (imágenes)                               │
│ ApiFlotaMID        │   build + push imagen   │ Entorno de Container Apps (solo consumo)     │
│ ApiWategay         │   + deploy Bicep        │   ├─ rodar-gateway  (KrakenD)   ◄─ PÚBLICO   │
└────────────────────┘                         │   ├─ rodar-tokens   (emite JWT)  interno     │
                                               │   ├─ flota-mid                   interno     │
                                               │   └─ flota-crud                  interno     │
                                               │ Cosmos DB para MongoDB (serverless)          │
                                               │ Log Analytics (con tope diario)              │
                                               └──────────────────────────────────────────────┘
```

* **Solo el gateway tiene URL pública.** El CRUD, el MID y el servicio de tokens son internos: solo se llega a ellos desde otro servicio del mismo entorno.
* El MID llama al CRUD **directo** (por la red interna) y a los otros grupos **por el gateway**, con su token.
* Cada repositorio despliega **su propia aplicación** al fusionar a `main`. La plataforma (ACR, Cosmos, entorno) se crea una sola vez.

Costos aproximados (región East US, modo de ahorro): ACR Basic ≈ 5 USD/mes; Cosmos DB serverless ≈ centavos con poco uso (0,25 USD por millón de RU y por GB); Container Apps de solo consumo con 0 réplicas en reposo ≈ 0 USD; logs con tope de 1 GB/día. **Con los 100 USD de Azure for Students sobra.** El único costo fijo es el ACR.

## 2. Qué necesita antes de empezar

| Qué | Para qué |
| --- | --- |
| Una suscripción de Azure (la de estudiantes sirve) | Donde se crea todo |
| [CLI de Azure](https://aka.ms/installazurecli) (`az`) y `az login` | Crear la plataforma y el acceso de GitHub |
| [CLI de GitHub](https://cli.github.com) (`gh`) y `gh auth login` | Guardar variables y secretos en los repositorios |
| Los tres repositorios en GitHub, con la rama `main` | Donde corre el CD |

No hace falta instalar nada más: Docker ya lo tiene, y el CD construye las imágenes en GitHub.

## 3. Configuración de una sola vez

Se hace **una vez por todo el equipo**, no por repositorio. Los pasos 1 y 2 están en este repositorio (`infra/scripts/`); el 3 en el del gateway.

### Paso 1. La plataforma

```bash
az login
infra/scripts/01-plataforma.sh
```

Crea el grupo `rg-rodar` (región `eastus`), el ACR, el entorno de Container Apps, Log Analytics y Cosmos DB. Pregunta antes de crear nada. Cambiar valores: `GRUPO=… UBICACION=… PREFIJO=… infra/scripts/01-plataforma.sh`.

Si la suscripción no permite alguna región, pruebe con otra (`UBICACION=eastus2`, `centralus`…): en Azure for Students las regiones permitidas varían.

### Paso 2. Que GitHub pueda desplegar (sin contraseñas)

```bash
DUENO=su-usuario-o-organizacion infra/scripts/02-acceso-github.sh
```

Registra una aplicación en Microsoft Entra ID, le da el rol *Contributor* **solo sobre `rg-rodar`**, la autoriza (federación OIDC) **únicamente para la rama `main` de cada uno de los tres repositorios**, y guarda en ellos las variables `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` y `AZURE_RESOURCE_GROUP`. No hay ninguna contraseña de Azure guardada en GitHub: GitHub pide un token temporal en cada despliegue.

Esas cuatro variables **no son secretas** (identifican, no autentican); por eso son *variables* y no *secretos* del repositorio.

### Paso 3. Los secretos de producción

En el repositorio `ApiWategay`: `scripts/03-secretos-produccion.sh`. Genera las llaves de firma, el secreto de cada servicio y las credenciales de cada cliente, y los guarda como *secretos* de GitHub en cada repositorio. Está explicado en `docs/despliegue-azure.md` de ese repositorio.

### Paso 4. Primer despliegue (en este orden)

Cada repositorio despliega al fusionar a `main` (o con **Actions → Despliegue a Azure → Run workflow**). La primera vez, en este orden, porque cada servicio necesita la dirección del anterior:

1. **ApiFlota** (el CRUD).
2. **ApiFlotaMID**.
3. **ApiWategay** (tokens y gateway).

Cada ejecución termina mostrando la dirección del servicio. Al final, el gateway imprime la URL pública: esa es la que se publica a los otros equipos.

Comprobación rápida:

```bash
curl https://<url-del-gateway>/health
curl -s -X POST https://<url-del-gateway>/token \
  -d grant_type=client_credentials -d client_id=administrador -d client_secret=<secreto> \
  -d scope=vehiculos:leer
```

## 4. Día a día

| Quiero… | Hago… |
| --- | --- |
| Publicar un cambio | PR a `develop` → CI en verde → fusionar. Para publicar: PR de `develop` a `main`; al fusionar, el CD despliega |
| Redesplegar sin cambios | **Actions → Despliegue a Azure → Run workflow** |
| Ver los logs | Portal de Azure → *rodar-entorno* → Logs, o `az containerapp logs show -n flota-crud -g rg-rodar --follow` |
| Tener todo encendido para una demostración | `infra/scripts/modo-demo.sh encendido` (y `ahorro` después) |
| Cambiar el secreto de un servicio | Vuelva a ejecutar el paso 3 y redespliegue los tres repositorios |

### Modo ahorro y modo demostración

Por defecto los servicios **escalan a cero** cuando no se usan, y no cuestan nada en reposo. La contrapartida: la **primera petición tras un rato sin uso tarda varios segundos** (arranque en frío) y, como el gateway y el MID esperan poco, **puede fallar**. Eso está bien para desarrollar y es un problema en una demostración o una prueba de otro equipo.

* Unas horas antes de presentar: `infra/scripts/modo-demo.sh encendido` (1 réplica siempre activa en cada servicio; unos pocos dólares al mes si se deja prendido).
* Después: `infra/scripts/modo-demo.sh ahorro`.

Los despliegues del CD conservan el valor que haya dejado.

## 5. Seguridad

* **Repositorios públicos, sin secretos dentro.** Ningún archivo versionado contiene llaves, contraseñas ni cadenas de conexión; todo sale de los secretos de GitHub y de Azure. Los `.env` y `credenciales-locales.json` están en `.gitignore`.
* **El workflow de CD corre solo en `main`**, y la credencial federada de Azure **solo acepta** ejecuciones de la rama `main` de cada repositorio: un fork o una rama no pueden desplegar.
* El CI (`ci.yml`) no usa secretos, así que es seguro con *pull requests* de forks.
* Se usan **ejecutores de GitHub** (`ubuntu-latest`). **No use ejecutores propios (self-hosted) con repositorios públicos**: cualquiera podría ejecutar código en su máquina con un PR.
* El CRUD solo acepta peticiones con la cabecera `X-Gateway-Secret`; como además no tiene URL pública, el secreto es una segunda barrera, no la única.
* En Azure: el ACR tiene el usuario administrador activado (lo usa Container Apps para descargar imágenes). Es una decisión de simplicidad para el proyecto; en producción real se usaría identidad administrada.

## 6. Qué se verificó y qué no

**Verificado (con herramientas locales):**

* Las plantillas Bicep compilan y pasan el *linter* (`az bicep build/lint`).
* Los *scripts* pasan `shellcheck`; los *workflows*, `actionlint`.
* La imagen de producción construye y arranca; el CRUD, el MID y el gateway funcionan juntos en Docker Compose (en el repositorio del gateway, `make up` y `make test`).
* Los tokens que emite el servicio propio los valida KrakenD con la misma configuración que usará en Azure: **solo cambian las variables de entorno**, no el código.

**No verificado (requiere una suscripción real):**

* El despliegue en sí. Los puntos con más riesgo están en la sección siguiente.

## Si algo falla

| Síntoma | Causa probable | Qué hacer |
| --- | --- | --- |
| El paso 1 falla en `databaseAccounts` con un error de capacidad | La plantilla pide el modo *serverless* de Cosmos con la sintaxis de la API y su suscripción o región no lo acepta | Cree la cuenta **a mano** en el portal: *Azure Cosmos DB for MongoDB (RU)*, capacidad **Serverless**, versión **7.0**. Vuelva a ejecutar el paso 1 con `COSMOS_EXISTENTE=<nombre de la cuenta>`, y cree esa variable en el repositorio (`gh variable set COSMOS_EXISTENTE --body <nombre>`) |
| El paso 1 falla con «region not available» o «quota» | Región no permitida en su suscripción | `UBICACION=otra-región` |
| El paso 2 falla en `az ad app create` | Su tenant (universidad) no deja registrar aplicaciones | Pídale a quien administre el tenant que registre una aplicación y la credencial federada (formato abajo), o use un usuario de otra cuenta con permiso. Mientras tanto, el CD no puede funcionar, pero todo lo demás sí |
| El CD falla en «Iniciar sesión en Azure» (`AADSTS70025` o `AADSTS700213`) | La credencial federada no coincide con el repositorio/rama | Revise que el nombre del repositorio y del dueño sean exactos y que despliegue desde `main` |
| El CD falla en `az acr login` | El grupo no tiene ACR o el rol no se propagó | Espere un minuto y reintente; confirme el paso 1 |
| La aplicación arranca y se reinicia | Revise `az containerapp logs show`. Lo más común: `MONGO_URI` mal, o Cosmos aún no listo | Mire el primer error en el log |
| El MID o el gateway no alcanzan al CRUD («connection refused»/certificado) | Dirección interna mal escrita, o el certificado del dominio interno | El valor correcto es el que imprime el CD del CRUD (`fqdnInterno`), con `https://` |
| Las primeras peticiones dan 500 y luego funcionan | Arranque en frío (réplicas en 0) | `infra/scripts/modo-demo.sh encendido` |

### Formato de la credencial federada (para quien administra el tenant)

* Emisor: `https://token.actions.githubusercontent.com`
* Sujeto: `repo:<dueño>/<repositorio>:ref:refs/heads/main`
* Audiencia: `api://AzureADTokenExchange`
* Rol: *Contributor* sobre el grupo de recursos `rg-rodar`.

## 7. Archivos de este repositorio

| Archivo | Qué es |
| --- | --- |
| `infra/plataforma.bicep` | Plataforma compartida (una vez) |
| `infra/app.bicep` | El CRUD en Container Apps (lo despliega el CD) |
| `infra/scripts/01-plataforma.sh` | Paso 1 |
| `infra/scripts/02-acceso-github.sh` | Paso 2 |
| `infra/scripts/modo-demo.sh` | Enciende/apaga el «siempre encendido» |
| `.github/workflows/ci.yml` | Pruebas y validación de Bicep en cada PR |
| `.github/workflows/cd.yml` | Despliegue a Azure al fusionar a `main` |
| `.github/pull_request_template.md` | Plantilla de PR |
