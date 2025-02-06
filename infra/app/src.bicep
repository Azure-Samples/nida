param name string
param location string = resourceGroup().location
param tags object = {}
param uniqueId string
param prefix string

param userAssignedIdentityResourceId string // param containerRegistryName string
param userAssignedIdentityClientId string
param userAssignedPrincipaLId string
param containerAppsEnvironmentName string
param applicationInsightsName string
param containerRegistry string = '${prefix}acr${uniqueId}'
param azureOpenaiResourceName string = 'nida' 
param azureOpenaiDeploymentName string = 'gpt-4o'
param azureWhisperDeploymentName string = 'whisper'
param azureOpenaiAudioDeploymentName string = 'gpt-4o-audio-preview'
param searchServiceName string = 'nida-aisearchh'

param functionName string = 'nida-func-${uniqueString(resourceGroup().id)}'
param funcContainerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
param mainContainerImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'


@description('Custom subdomain name for the OpenAI resource (must be unique in the region)')
param customSubDomainName string

@secure()
param appDefinition object

@description('Principal ID of the user executing the deployment')
param userPrincipalId string

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
// Cointainer for the storage account
resource storageQueue 'Microsoft.Storage/storageAccounts/queueServices/queues@2023-05-01' = {
  name: 'integration-queue'
  parent: queueServices
}

resource blobServices 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

// Cointainer for the storage account
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
              value: openai.properties.endpoint
            }
            {
              name: 'AZURE_OPENAI_DEPLOYMENT_NAME'
              value: openaideployment.name
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
              value: whisperDeployment.name
            }
            {
              name: 'AZURE_AUDIO_MODEL'
              value: audioDeployment.name
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


resource functionContainerApp 'Microsoft.App/containerApps@2023-05-02-preview' = {
  name: functionName
  location: location
  tags: union(tags, {'azd-service-name':  'functions' })
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
      ingress: {
        external: false
        targetPort: 80
        transport: 'auto'
      }
    }
    template: {
      scale: {
        minReplicas: 1
        maxReplicas: 1
      }
      containers: [
        {
          name: 'function'
          image: funcContainerImage
          resources: {
            cpu: 1
            memory: '2Gi'
          }
          env: [
            // https://learn.microsoft.com/en-us/answers/questions/1225865/unable-to-get-a-user-assigned-managed-identity-wor
            { name: 'AZURE_CLIENT_ID', value: userAssignedIdentityClientId }
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
          ]
        }
      ]
    }
  }
}

// Deploy the Azure Cognitive Search service
resource searchService 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: searchServiceName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userAssignedIdentityResourceId}': {}
    }
  }
  sku: {
    name: 'standard'
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http403'
      }
    }
    publicNetworkAccess: 'Enabled'
  }
}

resource openai 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: azureOpenaiResourceName
  location: location
  sku: {
    name: 'S0'
  }
  kind: 'OpenAI'
  properties: {
    customSubDomainName: customSubDomainName
  }
}

// Define the OpenAI deployment
resource openaideployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  name: azureOpenaiDeploymentName
  parent: openai
  sku: {
    name: 'GlobalStandard'
    capacity: 1
  }
  properties: {
    model: {
      name: 'gpt-4o'
      format: 'OpenAI'
      version: '2024-11-20'
    }
    versionUpgradeOption: 'OnceCurrentVersionExpired'
  }
}

// Define the Whisper deployment
// putting dependency on openai deployment just so that they deploy sequentially
resource whisperDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  name: azureWhisperDeploymentName
  parent: openai
  dependsOn: [ openaideployment ]
  sku: {
    name: 'Standard'
    capacity: 1
  }
  properties: {
    model: {
      // 'whisper' or 'whisper-base', etc. (Exact name depends on Azure OpenAI availability)
      name: 'whisper'
      format: 'OpenAI'
      version: '001'
    }
    // The rest depends on your configuration or scale settings
  }
}

// Define the OpenAI deployment
// putting dependency on whisper deployment just so that they deploy sequentially
resource audioDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  name: azureOpenaiAudioDeploymentName
  parent: openai
  dependsOn: [ whisperDeployment ]
  sku: {
    name: 'GlobalStandard'
    capacity: 8
  }
  properties: {
    model: {
      name: 'gpt-4o-audio-preview'
      format: 'OpenAI'
      version: '2024-12-17'
    }
    versionUpgradeOption: 'OnceCurrentVersionExpired'
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
  name: guid(dynamicsession.id, userPrincipalId, 'Azure Container Apps Session Executor')
  scope: dynamicsession
  properties: {
    principalId: userPrincipalId
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

resource userOpenaiRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openai.id, userPrincipalId, 'Cognitive Services OpenAI User')
  scope: openai
  properties: {
    principalId: userPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
  }
} 

resource appOpenaiRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openai.id, userAssignedIdentityResourceId, 'Cognitive Services OpenAI User')
  scope: openai
  properties: {
    principalId: userAssignedPrincipaLId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
  }
}

// (Replace the roleDefinitionId with the proper built-in role ID for your scenario.)
resource searchRoleAssignmentContrib 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  // Generate a deterministic GUID based on inputs.
  name: guid(searchService.id, userAssignedIdentityResourceId, 'Search Index Data Contributor')
  scope: searchService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '8ebe5a00-799e-43f5-93ac-243d3dce84a7')
    principalId: userAssignedPrincipaLId
    principalType: 'ServicePrincipal'
  }
}

resource searchRoleAssignmentIndexer 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  // Generate a deterministic GUID based on inputs.
  name: guid(searchService.id, userAssignedIdentityResourceId, 'Search Service Contributor')
  scope: searchService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7ca78c08-252a-4471-8644-bb5ff32d4ba0')
    principalId: userAssignedPrincipaLId
    principalType: 'ServicePrincipal'
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
      'ba92f5b4-2d11-453d-a403-e96b0029c9fe' // Storage Blob Data Contributor
    )
  }
}

resource storageQueueDataContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
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
  name: guid(storageAccount.id, userPrincipalId,'Storage Queue Data Reader')
  scope: storageAccount
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', '19e7f393-937e-4f77-808e-94535e297925')
    principalId: userPrincipalId
    principalType: 'User'
  }
}

resource storageAccountContributorRoleAssignmentUser 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(storageAccount.id, userPrincipalId, 'storageAccountContributor')
  scope: storageAccount
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', '17d1049b-9a84-46fb-8f53-869881c3d3ab')
    principalId: userPrincipalId
    principalType: 'User'
  }
}

output defaultDomain string = containerAppsEnvironment.properties.defaultDomain
output name string = app.name
output uri string = 'https://${app.properties.configuration.ingress.fqdn}'
output id string = app.id
output azure_endpoint string = openai.properties.endpoint
output pool_endpoint string = dynamicsession.properties.poolManagementEndpoint
