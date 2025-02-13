param searchServiceName string
param userAssignedIdentityResourceId string // param containerRegistryName string
param userAssignedPrincipaLId string
param currentUserT string
param currentUser string
param location string = resourceGroup().location

// Deploy the Azure Cognitive Search service
resource searchService 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: searchServiceName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${userAssignedIdentityResourceId}': {} }
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

// (Replace the roleDefinitionId with the proper built-in role ID for your scenario.)
resource searchRoleAssignmentContrib 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  // Generate a deterministic GUID based on inputs.
  name: guid(searchService.id, userAssignedPrincipaLId, 'searchServiceIndexContributor')
  scope: searchService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '8ebe5a00-799e-43f5-93ac-243d3dce84a7')
    principalId: userAssignedPrincipaLId
    principalType: 'ServicePrincipal'
  }
}

resource searchRoleAssignmentIndexer 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  // Generate a deterministic GUID based on inputs.
  name: guid(searchService.id, userAssignedPrincipaLId, 'searchServiceContributor')
  scope: searchService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7ca78c08-252a-4471-8644-bb5ff32d4ba0')
    principalId: userAssignedPrincipaLId
    principalType: 'ServicePrincipal'
  }
}

// (Replace the roleDefinitionId with the proper built-in role ID for your scenario.)
resource searchRoleAssignmentContribUser 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  // Generate a deterministic GUID based on inputs.
  name: guid(searchService.id, currentUser, 'Search Index Data Contributor')
  scope: searchService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '8ebe5a00-799e-43f5-93ac-243d3dce84a7')
    principalId: currentUser
    principalType: currentUserT
  }
}

resource searchRoleAssignmentIndexerUser 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = {
  // Generate a deterministic GUID based on inputs.
  name: guid(searchService.id, currentUser, 'Search Service Contributor')
  scope: searchService
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7ca78c08-252a-4471-8644-bb5ff32d4ba0')
    principalId: currentUser
    principalType: currentUserT
  }
}


output searchServiceName string = searchService.name
output endpoint string = 'https://${searchService.name}.search.windows.net'
