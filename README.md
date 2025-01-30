<!-- filepath: ./README.md -->
# Nida - A simple, yet powerful Contact Center Analytics Solution

Nida is a contact center analytics solution that allows you to analyze customer calls using AI. The solution supports easy creation of multiple persons to evaluate the calls and thus allows to extract department specific information. For example:

* Sales Quality Manager --> Able to easily extract insights about the agents' sales qualities, e.g., up-selling attempts, empathy, etc.
* Marketing Manager --> Extract sentiment, awareness regarding promotions, etc.
* Product Manager --> Extract product related issues and pain points of customers

The project consists of a multi-stage pipeline to process calls:

* Transcription via `whisper` or `gpt-4o-audio-preview`, subsequent diarization (if required) via `gpt-4o`
* Insight extraction via `gpt-4o`, based on user-defined personas
* Analytics based on PowerBI (optional)

## Getting Started

### Prerequisites

* Docker
* [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli)
* [Azure Developer CLI](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/install-azd)
* Available quota for Azure OpenAI in your Azure subscription (rates can be adjusted in `infra/app/src.bicep`):

| Model | Deloyment Type | Quota |
|---------|-------|------|
| gpt-4o (2024-11-20) | GlobalStandard | 30k TPM |
| whisper-001 | Standard | 3 RPM |
| gpt-4o-audio-preview (2024-12-17) | GlobalStandard | 80k TPM |

For example `swedencentral`

### Deployment to Azure (via `azd up`)

1. Clone the repo
1. `az login`
1. `azd up`

Then visit the `azurecontainerapps` URL that is returned. In the UI, you can upload the sample call `samples/test.mp3` and create a first persona from `samples/marketing_sentiment_details.txt`.

### Local deployment (manually)

1. `cd src`
1. `cp .env.sample .env` and update `.env` with your valid keys, endpoint, and settings
1. `pip install -r requirements.txt`
1. `streamlit run main.py`

### Local deployment (via `docker`)

`TODO`

## Overview

This project consists of:

- **`infra/`** – Bicep files for Azure infrastructure deployments.  
  - `app/src.bicep` is the main file to modify.
  - Refer to `azure.yaml` for basic service definitions, such as container app settings, Dockerfiles, and any optional resource group info (commented).

- **`src/`** – Main application code with a Streamlit app.  
  - `Main.py` sets up Streamlit configuration, page title, and loads a logo.
  - Other Python files (e.g., `transcriptions.py`) import services like `azure_storage` and `azure_transcription`.

- **`samples/`** – Sample person definition and sample audio call.