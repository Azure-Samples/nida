targetScope = 'resourceGroup'

param openAIName string

resource openAI 'Microsoft.CognitiveServices/accounts@2022-03-01' existing = {
  name: openAIName
}

output openAIEndpoint string = openAI.properties.endpoint
