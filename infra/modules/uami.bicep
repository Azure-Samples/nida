param location string = resourceGroup().location
param identityName string 

resource userAssignedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2018-11-30' = {
  name: identityName
  location: location
}

output identityId string = userAssignedIdentity.id
output clientId string = userAssignedIdentity.properties.clientId
output principalId string = userAssignedIdentity.properties.principalId
