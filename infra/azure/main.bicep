// Online Boutique v1 on Azure Container Apps (Phase 2).
//
// Deploys, into the target resource group:
//   - a Log Analytics workspace with a daily ingestion cap (stays in the 5 GB/month free grant)
//   - one Container Apps environment (Consumption plan)
//   - the 10 Online Boutique Container Apps (no load generator or shopping
//     assistant); cartservice carries Redis as a sidecar
//   - a free-tier Cosmos DB account for the v2 agent
//
// Every resource is tagged so costs can be split by component and version.
// Deploy with ./deploy.sh rather than calling this file directly.

targetScope = 'resourceGroup'

@description('Azure region for every resource.')
param location string = resourceGroup().location

@description('Short prefix for resource names.')
param namePrefix string = 'poc-gd'

@description('Registry that hosts the upstream Online Boutique images.')
param imageRegistry string = 'us-central1-docker.pkg.dev/online-boutique-ci/microservices-demo'

@description('Upstream Online Boutique release.')
param imageTag string = 'v0.10.7'

@description('Image for recommendationservice. v1 is the unmodified upstream image.')
param recommendationImage string = '${imageRegistry}/recommendationservice:${imageTag}'

@description('Frontend image. Defaults to upstream (9 products); set to the /catalog image once it is in a registry.')
param frontendImage string = '${imageRegistry}/frontend:${imageTag}'

@description('Product catalog image. Defaults to upstream (9 products); set to the /catalog image once it is in a registry.')
param productCatalogImage string = '${imageRegistry}/productcatalogservice:${imageTag}'

@description('0 = scale to zero when idle (free-tier friendly). 1 = always on (for demos).')
@minValue(0)
@maxValue(1)
param minReplicas int = 0

@description('Deploy the Cosmos DB account used by the v2 agent.')
param deployCosmos bool = true

@description('Daily Log Analytics ingestion cap in GB. 0.15 GB/day keeps under the 5 GB/month free grant.')
param logDailyQuotaGb string = '0.15'

var baseTags = {
  project: 'poc-group-d'
  course: 'coen6313'
  environment: 'dev'
}

var commonEnv = [
  { name: 'DISABLE_PROFILER', value: '1' }
  { name: 'ENABLE_PROFILER', value: '0' }
  { name: 'ENABLE_TRACING', value: '0' }
]

// Every internal service is reachable at "<app name>:80" inside the environment.
var addr = {
  productcatalog: 'productcatalogservice:80'
  currency: 'currencyservice:80'
  cart: 'cartservice:80'
  recommendation: 'recommendationservice:80'
  shipping: 'shippingservice:80'
  checkout: 'checkoutservice:80'
  ad: 'adservice:80'
  payment: 'paymentservice:80'
  email: 'emailservice:80'
}

var redisSidecar = {
  name: 'redis'
  image: 'docker.io/library/redis:7.4-alpine'
  resources: {
    cpu: json('0.25')
    memory: '0.5Gi'
  }
}

var services = [
  {
    name: 'frontend'
    image: frontendImage
    port: 8080
    external: true
    transport: 'http'
    version: 'shared'
    cpu: '0.25'
    memory: '0.5Gi'
    sidecars: []
    env: concat(commonEnv, [
      { name: 'PORT', value: '8080' }
      { name: 'PRODUCT_CATALOG_SERVICE_ADDR', value: addr.productcatalog }
      { name: 'CURRENCY_SERVICE_ADDR', value: addr.currency }
      { name: 'CART_SERVICE_ADDR', value: addr.cart }
      { name: 'RECOMMENDATION_SERVICE_ADDR', value: addr.recommendation }
      { name: 'SHIPPING_SERVICE_ADDR', value: addr.shipping }
      { name: 'CHECKOUT_SERVICE_ADDR', value: addr.checkout }
      { name: 'AD_SERVICE_ADDR', value: addr.ad }
      // Required by the frontend even though the shopping assistant is disabled.
      { name: 'SHOPPING_ASSISTANT_SERVICE_ADDR', value: 'shoppingassistantservice:80' }
    ])
  }
  {
    name: 'recommendationservice'
    image: recommendationImage
    port: 8080
    external: false
    transport: 'http2'
    version: 'v1'
    cpu: '0.25'
    memory: '0.5Gi'
    sidecars: []
    env: concat(commonEnv, [
      { name: 'PORT', value: '8080' }
      { name: 'PRODUCT_CATALOG_SERVICE_ADDR', value: addr.productcatalog }
    ])
  }
  {
    name: 'productcatalogservice'
    image: productCatalogImage
    port: 3550
    external: false
    transport: 'http2'
    version: 'shared'
    cpu: '0.25'
    memory: '0.5Gi'
    sidecars: []
    env: concat(commonEnv, [
      { name: 'PORT', value: '3550' }
    ])
  }
  {
    name: 'cartservice'
    image: '${imageRegistry}/cartservice:${imageTag}'
    port: 7070
    external: false
    transport: 'http2'
    version: 'shared'
    cpu: '0.25'
    memory: '0.5Gi'
    // Redis runs in the same replica instead of a paid managed cache. Cart
    // contents are lost when the app scales to zero, which is acceptable here.
    sidecars: [redisSidecar]
    env: [
      { name: 'REDIS_ADDR', value: 'localhost:6379' }
    ]
  }
  {
    name: 'checkoutservice'
    image: '${imageRegistry}/checkoutservice:${imageTag}'
    port: 5050
    external: false
    transport: 'http2'
    version: 'shared'
    cpu: '0.25'
    memory: '0.5Gi'
    sidecars: []
    env: concat(commonEnv, [
      { name: 'PORT', value: '5050' }
      { name: 'PRODUCT_CATALOG_SERVICE_ADDR', value: addr.productcatalog }
      { name: 'SHIPPING_SERVICE_ADDR', value: addr.shipping }
      { name: 'PAYMENT_SERVICE_ADDR', value: addr.payment }
      { name: 'EMAIL_SERVICE_ADDR', value: addr.email }
      { name: 'CURRENCY_SERVICE_ADDR', value: addr.currency }
      { name: 'CART_SERVICE_ADDR', value: addr.cart }
    ])
  }
  {
    name: 'currencyservice'
    image: '${imageRegistry}/currencyservice:${imageTag}'
    port: 7000
    external: false
    transport: 'http2'
    version: 'shared'
    cpu: '0.25'
    memory: '0.5Gi'
    sidecars: []
    env: concat(commonEnv, [
      { name: 'PORT', value: '7000' }
    ])
  }
  {
    name: 'paymentservice'
    image: '${imageRegistry}/paymentservice:${imageTag}'
    port: 50051
    external: false
    transport: 'http2'
    version: 'shared'
    cpu: '0.25'
    memory: '0.5Gi'
    sidecars: []
    env: concat(commonEnv, [
      { name: 'PORT', value: '50051' }
    ])
  }
  {
    name: 'shippingservice'
    image: '${imageRegistry}/shippingservice:${imageTag}'
    port: 50051
    external: false
    transport: 'http2'
    version: 'shared'
    cpu: '0.25'
    memory: '0.5Gi'
    sidecars: []
    env: concat(commonEnv, [
      { name: 'PORT', value: '50051' }
    ])
  }
  {
    name: 'emailservice'
    image: '${imageRegistry}/emailservice:${imageTag}'
    port: 8080
    external: false
    transport: 'http2'
    version: 'shared'
    cpu: '0.25'
    memory: '0.5Gi'
    sidecars: []
    env: concat(commonEnv, [
      { name: 'PORT', value: '8080' }
    ])
  }
  {
    name: 'adservice'
    image: '${imageRegistry}/adservice:${imageTag}'
    port: 9555
    external: false
    transport: 'http2'
    version: 'shared'
    // The Java service needs more memory than the others.
    cpu: '0.5'
    memory: '1Gi'
    sidecars: []
    env: [
      { name: 'PORT', value: '9555' }
    ]
  }
]

resource logs 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${namePrefix}-logs'
  location: location
  tags: union(baseTags, { component: 'monitoring' })
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    workspaceCapping: {
      dailyQuotaGb: json(logDailyQuotaGb)
    }
  }
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${namePrefix}-env'
  location: location
  tags: union(baseTags, { component: 'platform' })
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logs.properties.customerId
        sharedKey: logs.listKeys().primarySharedKey
      }
    }
    zoneRedundant: false
  }
}

module apps 'modules/container-app.bicep' = [for svc in services: {
  name: 'app-${svc.name}'
  params: {
    name: svc.name
    location: location
    environmentId: environment.id
    tags: union(baseTags, { component: svc.name, version: svc.version })
    image: svc.image
    targetPort: svc.port
    external: svc.external
    transport: svc.transport
    env: svc.env
    cpu: svc.cpu
    memory: svc.memory
    sidecars: svc.sidecars
    minReplicas: minReplicas
    maxReplicas: 1
  }
}]

module cosmos 'modules/cosmos.bicep' = if (deployCosmos) {
  name: 'cosmos'
  params: {
    location: location
    tags: union(baseTags, { component: 'recommendationservice', version: 'v2' })
    accountName: '${namePrefix}-cosmos-${uniqueString(resourceGroup().id)}'
  }
}

output frontendUrl string = 'https://${apps[0].outputs.fqdn}'
output environmentName string = environment.name
output cosmosAccountName string = cosmos.?outputs.accountName ?? ''
output cosmosEndpoint string = cosmos.?outputs.endpoint ?? ''
