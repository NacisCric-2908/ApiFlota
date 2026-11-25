// Plataforma compartida de Flota en Azure. Se despliega UNA sola vez (ver docs/despliegue-azure.md):
//   registro de contenedores (ACR) + registro de logs + entorno de Container Apps + Cosmos DB para MongoDB.
// Las aplicaciones (CRUD, MID, tokens y gateway) las despliega después el CD de cada repositorio.
//
// Costos (precios de la API de precios de Azure, región East US): ACR Basic ≈ $5/mes; Cosmos DB serverless ≈ $0,25 por
// millón de RU + $0,25 por GB; Log Analytics: 5 GB gratis al mes (aquí además con tope diario); el entorno de Container
// Apps de «solo consumo» no tiene costo fijo.
targetScope = 'resourceGroup'

@description('Prefijo para nombrar los recursos: minúsculas y números, de 3 a 12 caracteres.')
@minLength(3)
@maxLength(12)
param prefijo string = 'rodar'

@description('Región. Verifique que su suscripción (p. ej. Azure for Students) la permita.')
param ubicacion string = resourceGroup().location

@description('Si ya creó la cuenta de Cosmos DB a mano en el portal (modo serverless), escriba aquí su nombre y no se crea otra.')
param cosmosExistente string = ''

@description('Nombre de la base de datos de Flota en MongoDB.')
param nombreBaseDatos string = 'flota'

@description('Tope diario de ingesta de logs, en GB. Evita sorpresas en la factura.')
param topeDiarioLogsGb int = 1

var sufijo = uniqueString(resourceGroup().id)
var nombreAcr = '${prefijo}acr${sufijo}'
var nombreLogs = '${prefijo}-logs'
var nombreEntorno = '${prefijo}-entorno'
var nombreCosmos = empty(cosmosExistente) ? '${prefijo}-cosmos-${sufijo}' : cosmosExistente

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: nombreLogs
  location: ubicacion
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    workspaceCapping: {
      dailyQuotaGb: topeDiarioLogsGb
    }
  }
}

// Las imágenes de los cuatro servicios viven aquí. Basic incluye 10 GiB de almacenamiento.
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: nombreAcr
  location: ubicacion
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true // Container Apps descarga las imágenes con estas credenciales
  }
}

// Entorno de «solo consumo» (sin perfiles dedicados, que sí cobran una cuota fija por hora).
resource entorno 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: nombreEntorno
  location: ubicacion
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
  }
}

// Cosmos DB para MongoDB, API 7.0, modo serverless (sin mínimo mensual).
// NOTA: la capacidad «EnableServerless» no se pudo comprobar con un despliegue real. Si falla, cree la cuenta a mano en el
// portal (API for MongoDB, modo Serverless, versión 7.0) y vuelva a desplegar indicando su nombre en `cosmosExistente`.
resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = if (empty(cosmosExistente)) {
  name: nombreCosmos
  location: ubicacion
  kind: 'MongoDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    locations: [
      {
        locationName: ubicacion
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    apiProperties: {
      serverVersion: '7.0'
    }
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
  }
}

resource baseDeDatos 'Microsoft.DocumentDB/databaseAccounts/mongodbDatabases@2024-05-15' = if (empty(cosmosExistente)) {
  parent: cosmos
  name: nombreBaseDatos
  properties: {
    resource: {
      id: nombreBaseDatos
    }
  }
}

output nombreAcr string = acr.name
output servidorAcr string = acr.properties.loginServer
output nombreEntorno string = entorno.name
output dominioPorDefecto string = entorno.properties.defaultDomain
output nombreCosmos string = nombreCosmos
