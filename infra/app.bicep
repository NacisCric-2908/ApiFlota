// CRUD de Flota en Container Apps. Lo despliega el CD (.github/workflows/cd.yml) en cada cambio a main,
// con la imagen recién construida. Requiere haber desplegado antes infra/plataforma.bicep.
targetScope = 'resourceGroup'

@description('Debe ser el mismo prefijo que usó en plataforma.bicep.')
param prefijo string = 'rodar'

param ubicacion string = resourceGroup().location

@description('Imagen completa a desplegar, p. ej. rodaracrxxxx.azurecr.io/flota-crud:abc123.')
param imagen string

@description('Valor de GATEWAY_SECRET: el secreto que el gateway envía en X-Gateway-Secret a este servicio.')
@secure()
param gatewaySecret string

@description('Mismo valor que usó en plataforma.bicep si creó la cuenta de Cosmos a mano.')
param cosmosExistente string = ''

param nombreBaseDatos string = 'flota'
param nombreApp string = 'flota-crud'

@description('Cargar los 30 vehículos semilla al arrancar con la base vacía.')
param sembrar bool = true

@description('0 = escala a cero (no cuesta en reposo, pero la primera petición tarda unos segundos). 1 = siempre encendido.')
@minValue(0)
@maxValue(2)
param replicasMinimas int = 0

var sufijo = uniqueString(resourceGroup().id)
var nombreAcr = '${prefijo}acr${sufijo}'
var nombreEntorno = '${prefijo}-entorno'
var nombreCosmos = empty(cosmosExistente) ? '${prefijo}-cosmos-${sufijo}' : cosmosExistente

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: nombreAcr
}

resource entorno 'Microsoft.App/managedEnvironments@2024-03-01' existing = {
  name: nombreEntorno
}

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' existing = {
  name: nombreCosmos
}

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: nombreApp
  location: ubicacion
  properties: {
    managedEnvironmentId: entorno.id
    configuration: {
      activeRevisionsMode: 'Single'
      // Interno: solo el gateway y el MID del mismo entorno llegan a este servicio. No tiene URL pública.
      ingress: {
        external: false
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      registries: [
        {
          server: acr.properties.loginServer
          username: acr.listCredentials().username
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        {
          name: 'acr-password'
          value: acr.listCredentials().passwords[0].value
        }
        {
          name: 'mongo-uri'
          value: cosmos.listConnectionStrings().connectionStrings[0].connectionString
        }
        {
          name: 'gateway-secret'
          value: gatewaySecret
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'api'
          image: imagen
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'MONGO_URI'
              secretRef: 'mongo-uri'
            }
            {
              name: 'MONGO_DB'
              value: nombreBaseDatos
            }
            {
              name: 'GATEWAY_SECRET'
              secretRef: 'gateway-secret'
            }
            {
              name: 'SEED_ON_EMPTY'
              value: sembrar ? 'true' : 'false'
            }
          ]
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 10
              periodSeconds: 30
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: replicasMinimas
        maxReplicas: 2
      }
    }
  }
}

output nombreApp string = app.name
output fqdnInterno string = app.properties.configuration.ingress.fqdn
