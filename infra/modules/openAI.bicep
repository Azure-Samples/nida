
param openAIName string = ''
param location string = resourceGroup().location
param customSubDomainName string
param currentUser string
param azureOpenaiResourceName string = 'nidaa'
param azureOpenaiDeploymentName string = 'gpt-4o'
param azureWhisperDeploymentName string = 'whisper'
param azureOpenaiAudioDeploymentName string = 'gpt-4o-audio-preview'
param azureOpenAiEmbedding string = 'text-embedding-3-large'
param userAssignedIdentityPrincipalId string

// Determine if we need to create a new OpenAI resource
var createOpenAI = empty(openAIName)

// If openAIName is provided, reference the existing resource
resource openAIExisting 'Microsoft.CognitiveServices/accounts@2022-03-01' existing = if(!createOpenAI) {
  name: openAIName
}

// If openAIName is empty, create a new OpenAI resource.
resource OpenAICreate 'Microsoft.CognitiveServices/accounts@2024-10-01' = if(createOpenAI)  {
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
resource openaideployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = if(createOpenAI) {
  name: azureOpenaiDeploymentName
  parent: OpenAICreate
  sku: {
    name: 'GlobalStandard'
    capacity: 30
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
resource whisperDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = if(createOpenAI) {
  name: azureWhisperDeploymentName
  parent: OpenAICreate
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
resource audioDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = if(createOpenAI) {
  name: azureOpenaiAudioDeploymentName
  parent: OpenAICreate
  dependsOn: [ whisperDeployment ]
  sku: {
    name: 'GlobalStandard'
    capacity: 80
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

  // Define the OpenAI deployment
// putting dependency on whisper deployment just so that they deploy sequentially
resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = if(createOpenAI) {
name: azureOpenAiEmbedding
  parent: OpenAICreate
  dependsOn: [ audioDeployment ]
  sku: {
    name: 'Standard'
    capacity: 80
  }
  properties: {
    model: {
      name: azureOpenAiEmbedding
      format: 'OpenAI'
      version: '1'
    }
    versionUpgradeOption: 'OnceCurrentVersionExpired'
  }
}


// Use a conditional expression to select the resource reference for further operations.
resource openAIRoleAssignment 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(
    createOpenAI ? OpenAICreate.id : openAIExisting.id, 
    userAssignedIdentityPrincipalId, 
    'Cognitive Services OpenAI User'
  )
  scope: createOpenAI ? OpenAICreate : openAIExisting
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
    principalId: userAssignedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

resource userOpenaiRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (createOpenAI) {
  name: guid(
    OpenAICreate.id , 
    currentUser, 
    'Cognitive Services OpenAI User'
  )
  scope: OpenAICreate
  properties: {
    principalId: currentUser
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
  }
} 


// Output the endpoint from whichever resource is used.
output openAIEndpoint string = createOpenAI ? OpenAICreate.properties.endpoint : openAIExisting.properties.endpoint
