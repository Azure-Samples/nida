# Use a slim Python base image
FROM python:3.9-slim

# Create a working directory
WORKDIR /main

# Copy the requirements file into container
COPY requirements.txt .

# Install any needed packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your code, including misc, azure_oai, and azure_storage folders
COPY . .

# If you want the default port to be 80, you can do:
EXPOSE 80

#go inside the app folder
WORKDIR /main
# Run Streamlit on container start
CMD streamlit run Main.py --server.port=80 --server.address=0.0.0.0
