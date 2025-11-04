# Ollama Gemma

This folder contains the necessary files to build and deploy the Ollama Gemma application using Google Cloud Run.

## Prerequisites

- Install and configure the [Google Cloud CLI](https://cloud.google.com/sdk/docs/install).
- Enable the following APIs in your Google Cloud project:
  - Artifact Registry
  - Cloud Build
  - Cloud Run
  - Cloud Storage
- Ensure you have the following IAM roles:
  - Artifact Registry Admin
  - Cloud Build Editor
  - Cloud Run Admin
  - Project IAM Admin
  - Service Account User
  - Service Usage Consumer
  - Storage Admin
- Request `Total Nvidia L4 GPU allocation, per project per region` quota under Cloud Run Admin API.

## Steps to Build and Deploy

1. **Set up gcloud**

   Configure the Google Cloud CLI for your project and region:

   ```bash
   gcloud config set project PROJECT_ID
   gcloud config set run/region REGION
   ```

   Replace `PROJECT_ID` with your Google Cloud project ID and `REGION` with your desired deployment region.

2. **Build and Deploy the Cloud Run Service**

   Build and deploy the service to Cloud Run:

   ```bash
   gcloud run deploy ollama-gemma \
       --source . \
       --concurrency 4 \
       --cpu 8 \
       --set-env-vars OLLAMA_NUM_PARALLEL=4 \
       --gpu 1 \
       --gpu-type nvidia-l4 \
       --max-instances 1 \
       --memory 32Gi \
       --no-allow-unauthenticated \
       --no-cpu-throttling \
       --no-gpu-zonal-redundancy \
       --timeout=600
   ```

   Key flags:
   - `--concurrency 4`: Matches the value of the `OLLAMA_NUM_PARALLEL` environment variable.
   - `--gpu 1` with `--gpu-type nvidia-l4`: Assigns 1 NVIDIA L4 GPU to each instance.
   - `--no-allow-unauthenticated`: Restricts unauthenticated access.

3. **Test the Deployed Service**

   Use the Cloud Run developer proxy to test the service:

   ```bash
   gcloud run services proxy ollama-gemma --port=8080
   ```

   In a separate terminal, send a request:

   ```bash
   curl http://localhost:8080/api/generate -d '{
     "model": "gemma3:12b-it-qat",
     "prompt": "Why is the sky blue?",
     "stream": false
   }'
   ```

   This should return a streaming response from the model.

## Reference

For more details, refer to the [official tutorial](https://cloud.google.com/run/docs/tutorials/gpu-gemma-with-ollama#build-and-deploy).

## Local Setup

1. **Download and Install Ollama**

   Follow the instructions to download and install Ollama from the [official website](https://ollama.com/).

2. **Run Ollama Locally**

   Start the Ollama service with the `gemma3:12b-it-qat` model on port 8080:

   ```bash
   ollama run gemma3:12b-it-qat --port 8080
   ```

   This will start the service locally and make it accessible on `http://localhost:8080`.
