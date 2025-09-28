# TwinRAN-AIaaS — AI Model Serving Service

## Introduction

TwinRAN-AIaaS is the **AI service layer** of the TwinRAN project.  
It turns machine-learning models trained on **OAI/FlexRIC testbed data** into a **reusable, production-grade API** that can be consumed by external systems.  

Where earlier experiments focused on proving feasibility (e.g., predicting scheduling request success or throughput in controlled testbeds), this service emphasizes **deployment**:  

- AI models are no longer research artifacts but **serving components**.  
- Each model is packaged with **metadata (`.json`) + weights (`.pkl`)**.  
- The service automatically loads these models, exposes them via **standard REST endpoints**, and documents them with **Swagger/OpenAPI**.  

This approach bridges the gap between **5G/6G experimental datasets** and **AI-native automation frameworks**, providing a reproducible, containerized service for model inference.

---


---


## Model Serving API

This project is a Flask-based API for serving a trained models.  
It provides REST endpoints for health checks, model metadata, schema inspection, and predictions.  

Includes:
- ✅ **Flask + Blueprints** for clean structure  
- ✅ **Marshmallow schemas** for input/output validation  
- ✅ **Swagger UI** (`/apidocs`) powered by Flasgger + apispec  
- ✅ **CORS configurable** via environment variables  
- ✅ **Docker & docker-compose** ready  

---

## Prerequisites
- Python 3.11+
- Docker (>=20.10)
- docker-compose (v2 recommended)

## Project Outline

```
TwinRAN-AIaaS
├─ app/                 # Core application (Flask)
│  ├─ routes/           # REST endpoints (predict, meta)
│  ├─ schemas/          # Marshmallow schemas (validation, docs)
│  ├─ services/         # Model registry + prediction logic
│  ├─ __init__.py       # create_app(), Swagger, CORS
│  └─ config.py         # Environment-driven config
├─ ml-models/           # Trained models (.json metadata + .pkl weights)
├─ run_dev.py           # Dev entrypoint
├─ wsgi.py              # WSGI entrypoint for prod (gunicorn/waitress)
├─ Dockerfile           # Container image
├─ docker-compose.yml   # Local orchestration
├─ requirements.txt     # Python dependencies
└─ MockFrontend/        # Lightweight HTML client for manual tests
```

---

## What It Does

1. **Model Registry** (`app/services/model_registry.py`)  
   - Scans `ml-models/` for pairs of `<tag>.json` + `<tag>.pkl`.  
   - Loads model objects (pickle) and metadata (JSON).  
   - Exposes them under a unique tag (e.g., `RandomForestRegressor_win07`).  

2. **Prediction Service** (`app/services/predict.py`)  
   - Validates features against metadata (`feature_names`, `window_size`).  
   - Applies **normalization & scaling** (window mean scaling, noise mapping).  
   - Runs inference, unscales prediction, and returns results.  

3. **Schemas & Validation** (`app/schemas/`)  
   - Define strict input/output formats with Marshmallow.  
   - Keep docs and implementation consistent.  

4. **REST API Endpoints** (`app/routes/`)  
   - `/health` — service liveness  
   - `/models` — list available models  
   - `/model_info` — metadata of a specific model  
   - `/api/schema` — expected feature names + example payload  
   - `/api/predict` — return predictions for given features  

5. **Swagger UI** (`/apidocs/`)  
   - Interactive docs auto-generated from schemas.  
   - Supports trying out endpoints directly in the browser.  

---

## AI Service Perspective

The service is not tied to one model; it’s a **platform for serving any trained model** produced in TwinRAN AI workflows:

- **Data Source**: Datasets from OAI/FlexRIC testbeds (uplink/downlink throughput, PRB usage, noise levels).  
- **Model Families**: Decision Trees, Random Forests, Gradient Boosting, XGBoost — evaluated for throughput prediction and noise-aware performance modeling.  
- **Deployment Goal**: Package the best models as **production-ready AI services**, usable in RAN automation and digital twin frameworks.  

Thus, the **AI Service = trained models + runtime + REST API**.

---

## ⚙️ Configuration

All runtime parameters are env-driven (`.env` file or Docker env vars):

| Variable | Default | Purpose |
|----------|---------|---------|
| `CORS_ORIGINS` | `*` | Allowed origins (comma-separated) |
| `HOST` | `0.0.0.0` | Host bind |
| `PORT` | `8000` | Port bind |
| `MODELS_DIR` | `ml-models` | Where to look for models |
| `DEFAULT_MODEL_NAME` | `RandomForestRegressor_win07` | Fallback model if none specified |

---


## Running the Service

### 1. Local (Dev Mode)

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env           # adjust if needed
python run_dev.py
```

Browse to: [http://localhost:8000/apidocs/](http://localhost:8000/apidocs/)

---

### 2. Docker

```bash
docker-compose up --build
# or
docker build -t twinran-aiaas .
docker run -p 8000:8000 twinran-aiaas

# --- Save the built image to a tar file ---
docker save -o twinran-aiaas.tar twinran-aiaas:latest

# --- Load the image from the tar file ---
docker load -i twinran-aiaas.tar

# --- Run the loaded image (same as before) ---
docker run -p 9000:8000 twinran-aiaas  # map host port 9000 -> container port 8000, app reachable at http://localhost:9000

```

---

## Example API Calls

### Health
```bash
curl http://localhost:8000/health
```

### Models
```bash
curl http://localhost:8000/models
```

### Model Info
```bash
curl "http://localhost:8000/model_info?model=RandomForestRegressor_win07"
```

### Schema
```bash
curl "http://localhost:8000/api/schema?model=RandomForestRegressor_win07"
```

### Predict
```bash
curl -X POST http://localhost:8000/api/predict   -H "Content-Type: application/json"   -d '{
        "model": "RandomForestRegressor_win07",
        "features": {
          "DL_hist_t_minus_6": 5972.43,
          "DL_hist_t_minus_5": 5676.08,
          "DL_hist_t_minus_4": 6051.62,
          "DL_hist_t_minus_3": 6071.67,
          "DL_hist_t_minus_2": 5784.66,
          "DL_hist_t_minus_1": 6240.32,
          "DL_hist_t_minus_0": 5695.44,
          "noise_target": -100.0,
          "noise_other_1": -110.0
        }
      }'
```

Response:
```json
{
  "prediction": 6025.5,
  "model_tag": "RandomForestRegressor_win07"
}
```