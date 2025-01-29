<!-- filepath: ./README.md -->
# README

## Overview
This project consists of:
- **Infra** – Bicep files for Azure infrastructure deployments.  
  - `src.bicep` is the main file to modify.
  - Refer to `azure.yaml` for basic service definitions, such as container app settings, Dockerfiles, and any optional resource group info (commented).

- **src** – Main application code with a Streamlit app.  
  - To run locally, use:  
    ```bash
    streamlit run main.py
    ```
  - `Main.py` sets up Streamlit configuration, page title, and loads a logo.
  - Other Python files (e.g., `transcriptions.py`) import services like `azure_storage` and `azure_transcription`.

- **misc** – Additional supporting files needing updates as the project evolves.

## Environment Variables
A sample file (`.env.sample`) shows how to configure:
- **Azure OpenAI** settings (keys, endpoints, versions).
- **Storage** settings (account name, container, audio folder).
- **Cosmos DB** container configuration.
- **Optional** endpoints for other Azure services.

Edit or rename `.env.sample` to `.env` and populate the correct values before running or deploying.

## Infrastructure & Deployment
- Bicep scripts (`src.bicep`) define Azure resources. Update these as needed for resource provisioning.
- [azure.yaml](http://_vscodecontentref_/0) can help manage services and infra via Azure Developer CLI (e.g., container app deployment, region info).
- A `Dockerfile` (referenced in [azure.yaml](http://_vscodecontentref_/1)) is used for building and deploying the Streamlit service.

## Getting Started
1. Clone the repo and install dependencies.
2. Create or update `.env` with valid keys and endpoints.
3. Deploy infrastructure using Bicep and any CLI commands required.
4. Build and run the container (or run locally using Streamlit).

Customize these steps based on your workflow and Azure environment requirements.