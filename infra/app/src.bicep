param name string
param location string = resourceGroup().location
param tags object = {}
param uniqueId string
param prefix string

param userAssignedIdentityResourceId string // param containerRegistryName string
param userAssignedIdentityClientId string
param userAssignedPrincipaLId string
param currentUserT string
param containerAppsEnvironmentName string
param applicationInsightsName string
param containerRegistry string = '${prefix}acr${uniqueId}'

param openAiEndpoint string

param azureOpenaiDeploymentName string = 'gpt-4o'
param azureWhisperDeploymentName string = 'whisper'
param azureOpenaiAudioDeploymentName string = 'gpt-4o-audio-preview'
param azureOpenAiEmbedding string = 'text-embedding-3-large'

param mainContainerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

param searchServiceName string

@secure()
param appDefinition object

@description('Principal ID of the user executing the deployment')
param currentUser string

var appSettingsArray = filter(array(appDefinition.settings), i => i.name != '')
var secrets = map(filter(appSettingsArray, i => i.?secret != null), i => {
  name: i.name
  value: i.value
  secretRef: i.?secretRef ?? take(replace(replace(toLower(i.name), '_', '-'), '.', '-'), 32)
})
var env = map(filter(appSettingsArray, i => i.?secret == null), i => {
  name: i.name
  value: i.value
})


resource containerAppsEnvironment 'Microsoft.App/managedEnvironments@2023-11-02-preview' existing = {
  name: containerAppsEnvironmentName
}

resource applicationInsights 'Microsoft.Insights/components@2020-02-02' existing = {
  name: applicationInsightsName
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2022-09-01' = {
  name: '${name}${uniqueString(resourceGroup().id)}'
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
  }
}

resource queueServices 'Microsoft.Storage/storageAccounts/queueServices@2023-05-01' = {
  parent: storageAccount
  name: 'default'
}

resource blobServices 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

resource storageQueue 'Microsoft.Storage/storageAccounts/queueServices/queues@2023-05-01' = {
  parent: queueServices
  name: 'integration-queue'
}

resource storageContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2021-04-01' = {
  name: 'mainproject'
  parent: blobServices
  properties: {
    publicAccess: 'None'
  }
}

resource app 'Microsoft.App/containerApps@2023-05-02-preview' = {
  name: name
  location: location
  tags: union(tags, {'azd-service-name':  'src' })
  // dependsOn: [ acrPullRole ]
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${userAssignedIdentityResourceId}': {} }
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironment.id
    configuration: {
      registries: [
        {
          server: '${containerRegistry}.azurecr.io'
          identity: userAssignedIdentityResourceId
        }
      ]
      activeRevisionsMode: 'Single'
      ingress:  {
        external: true
        targetPort: 80
        transport: 'auto'
        stickySessions: {
          affinity: 'sticky'
      }
      }
      secrets: union([
      ],
      map(secrets, secret => {
        name: secret.secretRef
        value: secret.value
      }))
    }
    template: {
      containers: [
        {
          image: mainContainerImage
          name: 'main'
          env: union([
            {
              name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
              value: applicationInsights.properties.ConnectionString
            }
            {
              name: 'AZURE_OPENAI_ENDPOINT'
              value: openAiEndpoint
            }
            {
              name: 'AZURE_OPENAI_DEPLOYMENT_NAME'
              value: azureOpenaiDeploymentName
            }
            {
              name: 'POOL_MANAGEMENT_ENDPOINT'
              value: dynamicsession.properties.poolManagementEndpoint
            }
            {
              name: 'AZURE_CLIENT_ID'
              value: userAssignedIdentityClientId
            }
            {
              name: 'PORT'
              value: '80'
            }
            {
              name: 'STORAGE_ACCOUNT_NAME'
              value: storageAccount.name
            }
            {
              name: 'STORAGE_QUEUE_NAME'
              value: storageQueue.name
            }
            {
              name: 'DEFAULT_CONTAINER'
              value: storageContainer.name
            }
            {
              name: 'AZURE_WHISPER_MODEL'
              value: azureWhisperDeploymentName
            }
            {
              name: 'AZURE_AUDIO_MODEL'
              value: azureOpenaiAudioDeploymentName
            }
            {
              name: 'AZURE_OPENAI_EMBEDDING_MODEL'
              value: azureOpenAiEmbedding
            }
            {
              name: 'AZURE_SEARCH_ENDPOINT'
              value: 'https://${searchServiceName}.search.windows.net'
            }
         
          ],
          env,
          map(secrets, secret => {
            name: secret.name
            secretRef: secret.secretRef
          }))
          resources: {
            cpu: json('2.0')
            memory: '4.0Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 10
      }
    }
  }
}

resource dynamicsession 'Microsoft.App/sessionPools@2024-02-02-preview' = {
  name: 'sessionPool'
  location: location
  tags: {
    tagName1: 'tagValue1'
  }
  properties: {
    containerType: 'PythonLTS'
    dynamicPoolConfiguration: {
      cooldownPeriodInSeconds: 300
      executionType: 'Timed'
    }
    poolManagementType: 'Dynamic'
    scaleConfiguration: {
      maxConcurrentSessions: 20
      readySessionInstances: 2
    }
  }
}

resource userSessionPoolRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(dynamicsession.id, currentUser, 'Azure Container Apps Session Executor')
  scope: dynamicsession
  properties: {
    principalId: currentUser
    principalType: currentUserT
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '0fb8eba5-a2bb-4abe-b1c1-49dfad359bb0')
  }
} 

resource appSessionPoolRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(dynamicsession.id, userAssignedIdentityResourceId, 'Azure Container Apps Session Executor')
  scope: dynamicsession
  properties: {
    principalId: userAssignedPrincipaLId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '0fb8eba5-a2bb-4abe-b1c1-49dfad359bb0')
  }
}



resource storageBlobDataContributorRA 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, userAssignedIdentityResourceId, 'StorageBlobDataContributor')
  scope: storageAccount
  properties: {
    principalId: userAssignedPrincipaLId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      'ba92f5b4-2d11-453d-a403-e96b0029c9fe' 
    )
  }
}

resource storageBlobDataOwner 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, userAssignedIdentityResourceId, 'StorageBlobDataOwner')
  scope: storageAccount
  properties: {
    principalId: userAssignedPrincipaLId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      'b7e6dc6d-f1e8-4753-8033-0f276bb0955b' 
    )
  }
}

resource storageQueueDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, userAssignedIdentityResourceId, 'storageQueueDataContributor')
  scope: storageAccount
  properties: {
    principalId: userAssignedPrincipaLId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      '974c5e8b-45b9-4653-ba55-5f855dd0fb88' 
    )
  }
}

resource storageQueueDataSender 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storageAccount.id, userAssignedIdentityResourceId, 'Storage Queue Data Message Sender')
  scope: storageAccount
  properties: {
    principalId: userAssignedPrincipaLId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      'c6a89b2d-59bc-44d0-9896-0f6e12d7b80a' 
    )
  }
}

resource queueRoleAssignmentUser 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(storageAccount.id, currentUser,'Storage Queue Data Reader')
  scope: storageAccount
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', '19e7f393-937e-4f77-808e-94535e297925')
    principalId: currentUser
    principalType: currentUserT
  }
}

resource storageBlobContributorRoleAssignmentUser 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(storageAccount.id, currentUser, 'StorageBlobDataContributor')
  scope: storageAccount
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', 'ba92f5b4-2d11-453d-a403-e96b0029c9fe')
    principalId: currentUser
    principalType: currentUserT
  }
}

output defaultDomain string = containerAppsEnvironment.properties.defaultDomain
output name string = app.name
output uri string = 'https://${app.properties.configuration.ingress.fqdn}'
output id string = app.id
output pool_endpoint string = dynamicsession.properties.poolManagementEndpoint
output storageAccountName string = storageAccount.name
output storageAccountEndpoint string = storageAccount.properties.primaryEndpoints.blob
