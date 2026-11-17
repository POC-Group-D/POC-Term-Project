// Canary dashboard: an Azure Monitor workbook comparing v1 and v2 of
// recommendationservice. Deployed by dashboard.sh.
//
// - Traffic and errors per revision: Azure Monitor metrics (both versions).
// - v2 latency, AI decisions and tokens: v2's "recommendation served" log
//   lines in Log Analytics (v1 is the unmodified upstream image and does not
//   log each request).

param location string = resourceGroup().location
param workspaceName string = 'poc-gd-logs'
param appName string = 'recommendationservice'

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: workspaceName
}

resource app 'Microsoft.App/containerApps@2024-03-01' existing = {
  name: appName
}

// Every v2 decision, with the fields the canary criteria use.
var decisions = '''
let decisions = ContainerAppConsoleLogs_CL
| where ContainerAppName_s == 'recommendationservice' and Log_s has 'recommendation served'
| extend r = parse_json(Log_s)
| extend revision = RevisionName_s, outcome = tostring(r.outcome), latencyMs = todouble(r.latencyMs),
         tokens = toint(r.promptTokens) + toint(r.completionTokens);
'''

var summaryQuery = '''decisions
| summarize ["v2 requests"] = count(),
            ["p95 latency (ms)"] = round(percentile(latencyMs, 95)),
            ["AI decisions %"] = round(100.0 * countif(outcome in ("agent", "cached")) / count(), 1),
            ["fallbacks"] = countif(outcome == "fallback"),
            ["model calls"] = countif(outcome == "agent"),
            ["avg tokens per model call"] = round(avgif(tokens, outcome == "agent"))
  by revision
'''

var latencyQuery = '''decisions
| summarize ["p95 (ms)"] = percentile(latencyMs, 95) by bin(TimeGenerated, 1m)
'''

var outcomesQuery = '''decisions
| summarize count() by bin(TimeGenerated, 1m), outcome
'''

var tokensQuery = '''decisions
| where outcome == "agent"
| summarize ["avg tokens"] = avg(tokens) by bin(TimeGenerated, 1m)
'''

func logChart(name string, title string, query string, visualization string, workspaceId string, width string) object => {
  type: 3
  name: name
  customWidth: width
  content: {
    version: 'KqlItem/1.0'
    title: title
    query: query
    size: 0
    queryType: 0
    resourceType: 'microsoft.operationalinsights/workspaces'
    crossComponentResources: [workspaceId]
    timeContextFromParameter: 'TimeRange'
    visualization: visualization
  }
}

func metricChart(name string, title string, appId string, splitBy string) object => {
  type: 10
  name: name
  customWidth: '50'
  content: {
    chartId: name
    version: 'MetricsItem/2.0'
    title: title
    size: 0
    chartType: 2
    resourceType: 'microsoft.app/containerapps'
    metricScope: 0
    resourceIds: [appId]
    timeContextFromParameter: 'TimeRange'
    timeContext: { durationMs: 3600000 }
    metrics: [
      {
        namespace: 'microsoft.app/containerapps'
        metric: 'microsoft.app/containerapps--Requests'
        aggregation: 1
        splitBy: splitBy
      }
    ]
  }
}

var workbook = {
  version: 'Notebook/1.0'
  items: [
    {
      type: 1
      name: 'title'
      content: {
        json: '## Canary: recommendationservice v1 vs v2\nv1 = random picks (upstream). v2 = AI agent on Groq. Thresholds: [docs/canary-criteria.md](https://github.com/POC-Group-D/POC-Term-Project/blob/main/docs/canary-criteria.md). Data arrives 2-5 minutes late.'
      }
    }
    {
      type: 9
      name: 'parameters'
      content: {
        version: 'KqlParameterItem/1.0'
        parameters: [
          {
            id: 'time-range'
            version: 'KqlParameterItem/1.0'
            name: 'TimeRange'
            label: 'Time range'
            type: 4
            isRequired: true
            value: { durationMs: 3600000 }
            typeSettings: {
              selectableValues: [
                { durationMs: 1800000 }
                { durationMs: 3600000 }
                { durationMs: 14400000 }
                { durationMs: 86400000 }
                { durationMs: 604800000 }
              ]
            }
          }
        ]
      }
    }
    logChart('summary', 'v2 per revision: the canary measures over the selected time', '${decisions}${summaryQuery}', 'table', workspace.id, '100')
    metricChart('traffic', 'Availability and traffic: requests per revision (v1 and v2)', app.id, 'revisionName')
    metricChart('status', 'Errors: requests by status code category (5xx = failed)', app.id, 'statusCodeCategory')
    logChart('latency', 'Latency: v2 p95 response time (ms), threshold 2000', '${decisions}${latencyQuery}', 'timechart', workspace.id, '50')
    logChart('outcomes', 'Correctness: v2 answers by outcome (fallback = not an AI decision)', '${decisions}${outcomesQuery}', 'barchart', workspace.id, '50')
    logChart('tokens', 'Cost: v2 tokens per model call, threshold 1500 (Groq Free: $0)', '${decisions}${tokensQuery}', 'timechart', workspace.id, '50')
    {
      type: 1
      name: 'cost'
      customWidth: '50'
      content: {
        json: '### Azure cost\nThe $10 monthly budget (alerts at 50/80/100%) and spend per resource are in **Cost Management > Budgets** for the resource group. Resources are tagged `project`, `component` and `version`.'
      }
    }
  ]
  isLocked: false
  fallbackResourceIds: ['Azure Monitor']
}

resource dashboard 'Microsoft.Insights/workbooks@2023-06-01' = {
  name: guid(resourceGroup().id, 'canary-dashboard')
  location: location
  kind: 'shared'
  tags: {
    project: 'poc-group-d'
    course: 'coen6313'
    environment: 'dev'
    component: 'recommendationservice'
  }
  properties: {
    displayName: 'Canary dashboard: recommendationservice v1 vs v2'
    category: 'workbook'
    sourceId: 'Azure Monitor'
    serializedData: string(workbook)
  }
}

output dashboardId string = dashboard.id
