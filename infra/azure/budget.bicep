// Monthly cost budget for the project resource group, with e-mail alerts at
// 50%, 80% and 100% of actual spend and at 100% of forecast spend.
// Must be deployed before any billable resource (course requirement).

targetScope = 'resourceGroup'

@description('Monthly budget in the billing currency (USD for Azure for Students).')
param amount int = 10

@description('Addresses that receive the alert e-mails.')
param contactEmails array

@description('First day of the current month; budgets must start on the 1st.')
param startDate string = '${utcNow('yyyy-MM')}-01'

param budgetName string = 'poc-group-d-monthly'

var actualThresholds = [50, 80, 100]

resource budget 'Microsoft.Consumption/budgets@2023-11-01' = {
  name: budgetName
  properties: {
    category: 'Cost'
    amount: amount
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: startDate
    }
    notifications: union(
      toObject(actualThresholds, t => 'actual${t}', t => {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: t
        thresholdType: 'Actual'
        contactEmails: contactEmails
      }),
      {
        forecast100: {
          enabled: true
          operator: 'GreaterThanOrEqualTo'
          threshold: 100
          thresholdType: 'Forecasted'
          contactEmails: contactEmails
        }
      }
    )
  }
}

output budgetName string = budget.name
