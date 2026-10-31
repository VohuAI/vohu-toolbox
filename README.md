# vLLM Model Runner

A simple Docker Compose setup for running multiple models with
[vLLM](https://github.com/vllm-project/vllm), using one shared Compose
file and a separate environment file for each model.

The goal is to keep model-specific settings independent while sharing
common configuration such as API credentials and storage locations.

## Directory Structure

``` text
vllm/
├── compose.yaml
├── .env
├── .env.example
├── .gitignore
├── run-model.sh
└── models/
    ├── qwen-coder-7b.env
    ├── qwen-coder-14b.env
    └── qwen-odoo-8b.env
```

  -----------------------------------------------------------------------
  Path                                Purpose
  ----------------------------------- -----------------------------------
  `compose.yaml`                      Shared Docker Compose definition
                                      for a vLLM service

  `.env`                              Shared settings and secrets

  `.env.example`                      Example of the shared environment
                                      file; contains no real secrets

  `models/*.env`                      Configuration for an individual
                                      model

  `run-model.sh`                      Helper script to start a model by
                                      its configuration name
  -----------------------------------------------------------------------

## Requirements

-   Docker Engine
-   Docker Compose v2 (`docker compose`)
-   An NVIDIA GPU and a compatible NVIDIA Container Toolkit
    installation, if running vLLM with NVIDIA GPU acceleration
-   Sufficient system RAM, GPU memory, and disk space for the selected
    model

Check the installed versions:

``` bash
docker --version
docker compose version
nvidia-smi
```

## Configuration

### 1. Shared environment file

Create `.env` in the project root:

``` dotenv
# Shared configuration

VLLM_API_KEY=replace-with-a-secure-api-key

HF_HOME=/srv/ai/huggingface-cache
MODEL_STORAGE=/srv/ai/models

# Optional: set this if downloading gated Hugging Face models
HF_TOKEN=
```

Keep real credentials in `.env`. Do not commit this file to source
control.

Create `.env.example` with placeholder values so other users can see
which shared settings are required:

``` dotenv
VLLM_API_KEY=change-me

HF_HOME=/srv/ai/huggingface-cache
MODEL_STORAGE=/srv/ai/models

HF_TOKEN=
```

### 2. Model-specific environment files

Create one file per model under `models/`.

Example: `models/qwen-coder-7b.env`

``` dotenv
CONTAINER_NAME=vllm-qwen-coder-7b
VLLM_PORT=8001

MODEL_NAME=Qwen/Qwen2.5-Coder-7B-Instruct
SERVED_MODEL_NAME=local-model

GPU_MEMORY_UTILIZATION=0.90
MAX_MODEL_LEN=8192
```

Example: `models/qwen-odoo-8b.env`

``` dotenv
CONTAINER_NAME=vllm-qwen-odoo-8b
VLLM_PORT=8002

MODEL_NAME=Qwen/Qwen2.5-7B-Instruct
SERVED_MODEL_NAME=local-model

GPU_MEMORY_UTILIZATION=0.90
MAX_MODEL_LEN=8192
```

Use the configuration filename (without `.env`) as the model's
management name. For example, `qwen-coder-7b` maps to
`models/qwen-coder-7b.env`.

The values above are examples. Replace model identifiers and runtime
settings with values appropriate for your model and hardware.

### 3. Docker Compose file

Create `compose.yaml`:

``` yaml
services:
  vllm:
    image: vllm/vllm-openai:latest
    container_name: ${CONTAINER_NAME:-vllm}

    ports:
      - "${VLLM_PORT:-8000}:8000"

    environment:
      HF_HOME: /root/.cache/huggingface
      HF_TOKEN: ${HF_TOKEN:-}
      VLLM_API_KEY: ${VLLM_API_KEY}

    volumes:
      - ${HF_HOME:-/srv/ai/huggingface-cache}:/root/.cache/huggingface
      - ${MODEL_STORAGE:-/srv/ai/models}:/models

    ipc: host

    command:
      - --model
      - ${MODEL_NAME}
      - --served-model-name
      - ${SERVED_MODEL_NAME:-local-model}
      - --gpu-memory-utilization
      - "${GPU_MEMORY_UTILIZATION:-0.90}"
      - --max-model-len
      - "${MAX_MODEL_LEN:-8192}"

    restart: unless-stopped
```

This is a minimal starting point. Add any model-specific vLLM arguments
required by your workload. The container image tag, model options, and
GPU configuration should be pinned and validated for your environment
before production use.

## Running Models

### Option 1: Run a model directly

Use both environment files: the shared `.env` first, followed by the
model-specific file.

``` bash
docker compose \
  --env-file .env \
  --env-file models/qwen-coder-7b.env \
  -p qwen-coder-7b \
  -f compose.yaml \
  up -d
```

Start another model with its own configuration:

``` bash
docker compose \
  --env-file .env \
  --env-file models/qwen-odoo-8b.env \
  -p qwen-odoo-8b \
  -f compose.yaml \
  up -d
```

When the same variable is defined in multiple `--env-file` files, the
later file takes precedence. Therefore, model-specific values can
override shared defaults.

The Compose project name (`-p`) keeps each model's Compose resources
separate. The container name and host port must also be unique for
concurrently running models.

### Option 2: Use the helper script

The `run-model.sh` script avoids repeating the full Compose command.

Create `run-model.sh`:

``` bash
#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <model-name>"
    echo "Available models:"

    for file in models/*.env; do
        [[ -f "$file" ]] || continue
        basename "$file" .env
    done

    exit 1
fi

MODEL="$1"
MODEL_ENV="models/${MODEL}.env"

if [[ ! -f "$MODEL_ENV" ]]; then
    echo "Error: Model configuration not found: $MODEL_ENV"
    exit 1
fi

docker compose \
    --env-file .env \
    --env-file "$MODEL_ENV" \
    -p "$MODEL" \
    -f compose.yaml \
    up -d
```

Make the script executable:

``` bash
chmod +x run-model.sh
```

Start a model:

``` bash
./run-model.sh qwen-coder-7b
```

List available model configurations:

``` bash
./run-model.sh
```

The script starts the service in detached mode. It does not
automatically stop other model projects.

## Managing a Running Model

Use the same project name and environment files when operating on a
model.

The `model-manager` script can start or stop a model using its configuration:

``` bash
./model-manager start -m qwen-coder-7b
./model-manager stop -m qwen-coder-7b
```

Run `./model-manager` without arguments to choose a command and model
interactively.

### View logs

``` bash
docker compose \
  --env-file .env \
  --env-file models/qwen-coder-7b.env \
  -p qwen-coder-7b \
  -f compose.yaml \
  logs -f
```

### Stop and remove the model container

``` bash
docker compose \
  --env-file .env \
  --env-file models/qwen-coder-7b.env \
  -p qwen-coder-7b \
  -f compose.yaml \
  down
```

### List running containers

``` bash
docker ps
```

### Check GPU usage

``` bash
nvidia-smi
```

## API Access

With the example configuration, the coding model is exposed on host port
`8001`.

For example:

``` bash
curl http://localhost:8001/v1/models \
  -H "Authorization: Bearer replace-with-a-secure-api-key"
```

Send a chat completion request:

``` bash
curl http://localhost:8001/v1/chat/completions \
  -H "Authorization: Bearer replace-with-a-secure-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "local-model",
    "messages": [
      {
        "role": "user",
        "content": "Write a Python function that adds two numbers."
      }
    ]
  }'
```

Use the actual API key and the `SERVED_MODEL_NAME` configured for the
selected model.

## Storage and Model Cache

The example Compose file mounts persistent host directories:

-   `/srv/ai/huggingface-cache` stores the Hugging Face cache.
-   `/srv/ai/models` is mounted at `/models` inside the container for
    locally stored model artifacts.

Create the directories before starting the service:

``` bash
sudo mkdir -p /srv/ai/huggingface-cache
sudo mkdir -p /srv/ai/models
```

The Hugging Face cache can be shared by multiple containers, avoiding
repeated downloads of the same files. Do not modify or replace model
files while a running vLLM process is using them.

## GPU Memory Considerations

Running multiple vLLM containers does not guarantee that multiple models
can fit on the same GPU.

`GPU_MEMORY_UTILIZATION` controls the fraction of GPU memory that a vLLM
instance is configured to use. It is not a reservation mechanism that
safely partitions GPU memory between containers.

Before running multiple models concurrently:

1.  Check available VRAM with `nvidia-smi`.
2.  Estimate the memory required by each model, including KV cache.
3.  Start with conservative settings.
4.  Monitor GPU memory and service logs.
5.  Adjust model size, context length, concurrency, or deployment
    strategy as needed.

If GPU memory is limited, run only one model at a time until concurrent
operation has been tested.

## Security and Git

A suggested `.gitignore`:

``` gitignore
.env
models/*.env
```

This ignores the shared secrets file and all model environment files. If
model-specific configuration contains no secrets and should be
version-controlled, use a different policy: keep non-sensitive model
configuration in tracked YAML files and store secrets separately.

Never commit API keys, Hugging Face tokens, or other credentials.

## Naming Convention

Use lowercase names with hyphens:

``` text
<model-family>-<purpose>-<size>.env
```

Examples:

``` text
qwen-coder-7b.env
qwen-coder-14b.env
qwen-odoo-8b.env
qwen-general-8b.env
```

Keep the filename, Compose project name, and container name related but
distinct:

-   Configuration: `models/qwen-coder-7b.env`
-   Compose project: `qwen-coder-7b`
-   Container: `vllm-qwen-coder-7b`

This makes it easier to identify and manage each model independently.

## Design Principles

This setup intentionally starts small:

-   One shared Compose file defines how a vLLM container runs.
-   Each model has its own environment file.
-   Shared credentials and storage settings live in the root `.env`.
-   Each model runs as an independent Compose project.
-   Model files and Hugging Face cache are stored persistently on the
    host.

As the environment grows, this structure can be extended with a model
registry, an API gateway, automated model routing, monitoring, and model
lifecycle workflows without changing the basic separation between shared
infrastructure and model-specific configuration.
