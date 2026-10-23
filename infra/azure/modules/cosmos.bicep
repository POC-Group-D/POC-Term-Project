// Azure Cosmos DB (NoSQL API) on the free tier, used by the v2 AI agent to
// store one document per recommendation request: the cart context it saw,
// the products it chose, the tools it called and the model tokens it used.
//
// Free tier covers 1000 RU/s and 25 GB per subscription. The account-level
// throughput limit below makes it impossible to provision past that.

param location string
param tags object

@description('Globally unique account name (3-44 chars, lowercase).')
param accountName string

param databaseName string = 'recommendations'
param containerName string = 'agent-decisions'

@description('Shared database throughput in RU/s (400 is the minimum).')
param databaseThroughput int = 400

@description('Documents expire after this many seconds (default 30 days).')
param defaultTtlSeconds int = 2592000

resource account 'Microsoft.DocumentDB/databaseAccounts@2024-05-15' = {
  name: accountName
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    // Always free tier: deploy.sh skips Cosmos DB rather than create a billed account.
    enableFreeTier: true
    capacity: {
      totalThroughputLimit: 1000
    }
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
    backupPolicy: {
      type: 'Periodic'
      periodicModeProperties: {
        backupIntervalInMinutes: 240
        backupRetentionIntervalInHours: 8
        backupStorageRedundancy: 'Local'
      }
    }
    minimalTlsVersion: 'Tls12'
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2024-05-15' = {
  parent: account
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
    options: {
      throughput: databaseThroughput
    }
  }
}

resource container 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2024-05-15' = {
  parent: database
  name: containerName
  properties: {
    resource: {
      id: containerName
      partitionKey: {
        paths: ['/userId']
        kind: 'Hash'
      }
      defaultTtl: defaultTtlSeconds
    }
  }
}

output accountName string = account.name
output endpoint string = account.properties.documentEndpoint
output databaseName string = database.name
output containerName string = container.name
