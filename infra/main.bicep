targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment that can be used as part of naming resource convention')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
@allowed([
  'northcentralusstage'
  'westus2'
  'northeurope'
  'eastasia'
  'northcentralus'
  'polandcentral'
  'italynorth'
  'switzerlandnorth'
  'swedencentral'
  'norwayeast'
  'japaneast'
  'australiaeast'
  'westcentralus'
]) // limit to regions where Dynamic sessions are available as of 2024-11-29
param location string

@secure()
param srcDefinition object

@description('Id of the user or app to assign application roles')
param principalId string

var tags = {
  'azd-env-name': environmentName
}

@description('Name of the existing Azure OpenAI resource')
param openAIName string

@description('Name of  the existing Azure Resource Group where the OpenAI resource is located')
param openAIResourceGroupName string

param runningOnGh string =''
var currentUserType = empty(runningOnGh) ? 'User' : 'ServicePrincipal'
var createOpenAI = empty(openAIName)

var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = toLower(uniqueString(rg.id, environmentName, location))

resource rg 'Microsoft.Resources/resourceGroups@2022-09-01' = {
  name: 'rg-nidat-${uniqueString(environmentName, location)}'
  location: location
  tags: tags
}

module monitoring './shared/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    location: location
    tags: tags
    logAnalyticsName: '${abbrs.operationalInsightsWorkspaces}${resourceToken}'
    applicationInsightsName: '${abbrs.insightsComponents}${resourceToken}'
  }
  scope: rg
}

module dashboard './shared/dashboard-web.bicep' = {
  name: 'dashboard'
  params: {
    name: '${abbrs.portalDashboards}${resourceToken}'
    applicationInsightsName: monitoring.outputs.applicationInsightsName
    location: location
    tags: tags
  }
  scope: rg
}


var uniqueId = uniqueString(rg.id)
param prefix string = 'dev'

module uami './modules/uami.bicep' = {
  name: 'uami'
  scope: rg
  params: {
    identityName: '${abbrs.managedIdentityUserAssignedIdentities}nida-${resourceToken}'
    location: location
  }
}

module openAI './modules/openAI.bicep' = if(createOpenAI) {
  name: 'openAI'
  scope: rg 
  params: {
    userAssignedIdentityPrincipalId: uami.outputs.principalId
    currentUser: principalId
    customSubDomainName: 'nidaa-${resourceToken}'
  }
}

// If openAIName is provided, reference the existing resource
resource openAIExisting 'Microsoft.CognitiveServices/accounts@2022-03-01' existing = if(!createOpenAI) {
  scope: resourceGroup(openAIResourceGroupName)
  name: openAIName
}

resource openAIRoleAssignment 'Microsoft.Authorization/roleAssignments@2020-04-01-preview' = if(!createOpenAI) {
  name: guid(openAIExisting.id, openAIExisting.id, 'Cognitive Services OpenAI User')
  
  properties: {
    roleDefinitionId: resourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
    principalId: uami.outputs.principalId
    principalType: 'ServicePrincipal'
  }
}

module appsEnv './shared/apps-env.bicep' = {
  name: 'apps-env'
  params: {
    name: '${abbrs.appManagedEnvironments}${resourceToken}'
    location: location
    tags: tags
    userAssignedIdentityResourceId: uami.outputs.identityId
    applicationInsightsName: monitoring.outputs.applicationInsightsName
    logAnalyticsWorkspaceName: monitoring.outputs.logAnalyticsWorkspaceName
  }
  scope: rg
}


module acrModule './modules/acr.bicep' = {
  name: 'acr'
  scope: rg
  params: {
    uniqueId: uniqueId
    prefix: prefix
    userAssignedIdentityPrincipalId: uami.outputs.principalId
    location: location
  }
}

module searchModule './modules/search.bicep' = {
  name: 'search'
  scope: rg
  params: {
    searchServiceName: '${abbrs.searchSearchServices}nida-${resourceToken}'
    userAssignedIdentityResourceId: uami.outputs.identityId
    userAssignedPrincipaLId: uami.outputs.principalId
    currentUserT: currentUserType
    currentUser: principalId
    location: location
  }
}


module src './app/src.bicep' = {
  name: 'nida'
  params: {
    name: 'nida'
    location: location
    uniqueId: uniqueId
    prefix: prefix
    userAssignedIdentityResourceId: uami.outputs.identityId
    userAssignedIdentityClientId: uami.outputs.clientId
    userAssignedPrincipaLId: uami.outputs.principalId
    currentUserT: currentUserType
    tags: tags
    openAiEndpoint: createOpenAI ? openAI.outputs.openAIEndpoint : openAIExisting.properties.endpoint
    applicationInsightsName: monitoring.outputs.applicationInsightsName
    containerAppsEnvironmentName: appsEnv.outputs.name
    appDefinition: srcDefinition
    currentUser: principalId
    containerRegistry: acrModule.outputs.acrName
    searchServiceName: searchModule.outputs.searchServiceName
  }
  scope: rg
}

output AZURE_OPENAI_ENDPOINT string = createOpenAI ? openAI.outputs.openAIEndpoint : openAIExisting.properties.endpoint
output POOL_MANAGEMENT_ENDPOINT string = src.outputs.pool_endpoint
output AZURE_RESOURCE_GROUP string = rg.name
output AZURE_TENANT_ID string = subscription().tenantId
output AZURE_USER_ASSIGNED_IDENTITY_ID string = uami.outputs.identityId
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = acrModule.outputs.acrEndpoint
