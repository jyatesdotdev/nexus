# Nexus Dev Infra

Supporting infrastructure for local development.

## 1. Core Services (Docker Compose)
These services run as standard Docker containers.

```bash
docker compose up -d
```
*   **PostgreSQL**: `localhost:5432` (User: `nexus`, Pass: `password`, DB: `nexus_dev`)
*   **Redis**: `localhost:6379`
*   **Grafana**: `localhost:3000` (User: `admin`, Pass: `admin`)

## 2. ML Models (Docker Model Runner)
To leverage MLX on your Mac, we use the **Docker Model Runner (DMR)** with the `vllm-metal` backend. This runs models natively on your GPU for peak performance.

### Setup Runner
Install the MLX-compatible backend:
```bash
docker model install-runner --backend vllm-metal
```

### Running Models
You can now run any MLX-optimized model from the [MLX Community on Hugging Face](https://huggingface.co/mlx-community).

**Llama 3.2 (3B Instruct):**
```bash
docker model run hf.co/mlx-community/Llama-3.2-3B-Instruct-4bit
```

**Qwen 2.5 Coder (7B Instruct):**
```bash
docker model run hf.co/mlx-community/Qwen2.5-Coder-7B-Instruct-4bit
```

### Accessing the API
The runner exposes an OpenAI-compatible API at `http://localhost:8000/v1`.
```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mlx-community/Llama-3.2-3B-Instruct-4bit",
    "messages": [{"role": "user", "content": "Explain quantum computing."}]
  }'
```