// One Online Boutique service as an Azure Container App.
//
// Internal services expose plaintext gRPC (HTTP/2) on port 80 inside the
// Container Apps environment, so callers reach them at "<name>:80".
// Only apps with external = true get a public HTTPS endpoint.

@description('Container App name. Also the DNS name other apps use to call it.')
param name string

param location string
param environmentId string
param tags object

@description('Main container image.')
param image string

@description('Port the main container listens on.')
param targetPort int

@description('true for the public frontend, false for internal gRPC services.')
param external bool = false

@description('http for the browser-facing frontend, http2 for gRPC services.')
@allowed(['http', 'http2'])
param transport string = 'http2'

param env array = []

@description('vCPU for the main container (string, e.g. "0.25").')
param cpu string = '0.25'

@description('Memory for the main container (e.g. "0.5Gi"). Must pair with cpu.')
param memory string = '0.5Gi'

@description('Extra containers in the same replica (e.g. a Redis sidecar).')
param sidecars array = []

@description('0 lets the app scale to zero when idle (no cost while idle).')
@minValue(0)
param minReplicas int = 0

@minValue(1)
param maxReplicas int = 1

resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: name
  location: location
  tags: tags
  properties: {
    managedEnvironmentId: environmentId
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: external
        targetPort: targetPort
        transport: transport
        // Internal gRPC is plaintext h2c; an HTTPS redirect would break it.
        allowInsecure: !external
      }
    }
    template: {
      containers: concat([
        {
          name: name
          image: image
          env: env
          resources: {
            cpu: json(cpu)
            memory: memory
          }
        }
      ], sidecars)
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
      }
    }
  }
}

output fqdn string = app.properties.configuration.ingress.fqdn
