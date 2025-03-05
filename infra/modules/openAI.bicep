targetScope = 'resourceGroup'

param openAIName string = ''
param userAssignedIdentityPrincipalId string

// Determine if we need to create a new OpenAI resource
var createOpenAI = empty(openAIName)

// If openAIName is provided, reference the existing resource
resource openAIExisting 'Microsoft.CognitiveServices/accounts@2022-03-01' existing = if(!createOpenAI) {
  name: openAIName
}

// If openAIName is empty, create a new OpenAI resource.
// You may want to parameterize or otherwise generate the new resource name.
resource openAICreate 'Microsoft.CognitiveServices/accounts@2022-03-01' = if(createOpenAI) {
  name: 'myNewOpenAIResource' // Change this to your naming convention
  location: resourceGroup().location
  sku: {
    name: 'S0'
  }
  kind: 'OpenAI'
  properties: {
    // Include any required properties here.
  }
}

// Use a conditional expression to select the resource reference for further operations.
resource openAIRoleAssignment 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  name: guid(
    createOpenAI ? openAICreate.id : openAIExisting.id, 
    userAssignedIdentityPrincipalId, 
    'Cognitive Services OpenAI User'
  )
  scope: createOpenAI ? openAICreate : openAIExisting
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
    principalId: userAssignedIdentityPrincipalId
    principalType: 'ServicePrincipal'
  }
}

// Output the endpoint from whichever resource is used.
output openAIEndpoint string = createOpenAI ? openAICreate.properties.endpoint : openAIExisting.properties.endpoint
