# Conductometric Titration Analyzer -- Backend

A Django REST API that performs conductometric titration analysis, including dilution correction, region splitting, linear regression, and equivalence point calculation.

---

## Table of Contents

1. [Overview](#overview)
2. [Project Structure](#project-structure)
3. [Prerequisites](#prerequisites)
4. [Local Development Setup](#local-development-setup)
5. [API Reference](#api-reference)
6. [Core Algorithm](#core-algorithm)
7. [Running Tests](#running-tests)
8. [Deployment](#deployment)
9. [Configuration Reference](#configuration-reference)

---

## Overview

This backend receives experimental conductometric titration data (volumes and conductivities), processes it through a scientific calculation pipeline, and returns the equivalence point, regression statistics, and angle between regression lines. It also provides CSV download endpoints for exporting input data and analysis results.

The calculation module is a Fortran-to-Python port that implements:
- Dilution correction
- Strong acid splitting (minimum conductivity)
- Weak acid splitting (maximum difference-delta)
- Least-squares linear regression (MLSF)
- Equivalence point determination via line intersection
- Angle calculation between regression lines

---

## Project Structure

```
backend/
  config/
    settings.py       -- Django settings (CORS, installed apps, middleware)
    urls.py            -- Root URL configuration (mounts /api/ and /admin/)
    wsgi.py            -- WSGI entry point for production servers
    asgi.py            -- ASGI entry point
  titration/
    calculation.py     -- Core scientific calculation module
    serializers.py     -- DRF input validation serializer
    views.py           -- API view functions (calculate, download-input, download-results)
    urls.py            -- App URL routes
    tests.py           -- Unit tests for the calculation module
    models.py          -- Empty (no database models needed)
    admin.py           -- Empty
    apps.py            -- App configuration
  manage.py            -- Django management script
  requirements.txt     -- Python dependencies
```

---

## Prerequisites

- Python 3.10 or later
- pip (Python package manager)
- Virtual environment tool (venv, virtualenv, or conda)

---

## Local Development Setup

1. Create and activate a virtual environment:

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r backend/requirements.txt
```

3. Run database migrations (required for Django admin, optional for the API):

```bash
python backend/manage.py migrate
```

4. Start the development server:

```bash
python backend/manage.py runserver 8000
```

The API will be available at `http://localhost:8000/api/`.

---

## API Reference

### POST /api/calculate/

Performs conductometric titration analysis on the provided data.

**Request Body (JSON):**

| Field            | Type         | Required | Description                                |
|------------------|-------------|----------|--------------------------------------------|
| volumes          | float[]      | Yes      | List of titrant volumes in mL (min 3)      |
| conductivities   | float[]      | Yes      | List of measured conductivity values (min 3)|
| acid_type        | string       | Yes      | "strong" or "weak"                         |
| v0               | float        | Yes      | Initial volume of acid solution in mL      |
| apply_dilution   | boolean      | No       | Whether to apply dilution correction (default: true) |

**Example Request:**

```json
{
  "volumes": [0, 5, 10, 15, 20, 25],
  "conductivities": [43.9, 38.6, 33.5, 28.7, 24.1, 32.0],
  "acid_type": "strong",
  "v0": 50,
  "apply_dilution": true
}
```

**Response (200 OK):**

```json
{
  "equivalence_point": {
    "volume": 20.52238,
    "conductivity": 35.22984
  },
  "angle": 85.54,
  "region_A": {
    "slope": -0.4406,
    "intercept": 44.272,
    "r_squared": 0.97873
  },
  "region_B": {
    "slope": 2.852,
    "intercept": -23.3,
    "r_squared": 1.0
  },
  "corrected_data": [[0, 43.9], [5, 42.46], [10, 40.2], ...]
}
```

**Error Responses:**
- 400 Bad Request -- Validation errors (missing fields, wrong types, mismatched lengths)
- 422 Unprocessable Entity -- Calculation errors (insufficient data, parallel lines)

---

### POST /api/download-input/

Downloads the input data as a CSV file.

**Request Body (form-encoded):**

| Field     | Type   | Description                              |
|-----------|--------|------------------------------------------|
| json_data | string | JSON string containing `volumes` and `conductivities` arrays |

**Response:** CSV file with `Content-Disposition: attachment; filename="titration_input_data.csv"`

---

### POST /api/download-results/

Downloads the analysis results as a CSV file.

**Request Body (form-encoded):**

| Field     | Type   | Description                              |
|-----------|--------|------------------------------------------|
| json_data | string | JSON string containing the full result object and `acid_type` |

**Response:** CSV file with `Content-Disposition: attachment; filename="titration_results.csv"`

---

## Core Algorithm

The `calculation.py` module implements the following pipeline:

1. **Dilution Correction**: Adjusts measured conductivities using the formula `Y_corrected = Y_measured * (V0 + v) / V0`.

2. **Region Splitting**:
   - Strong acids: Splits at the index of minimum conductivity.
   - Weak acids: Splits at the index where the second-order difference of conductivities is maximized.

3. **Linear Regression**: Performs least-squares regression on each region independently, computing slope, intercept, R-squared, and standard deviation.

4. **Equivalence Point**: Calculates the intersection of the two regression lines. The x-coordinate gives the equivalence volume, and the y-coordinate gives the conductivity at the equivalence point.

5. **Angle Calculation**: Computes the angle between the two regression lines using `arctan(|(m1 - m2) / (1 + m1 * m2)|)`. For weak acids, the angle is supplemented to 180 degrees.

### Key Functions

| Function              | Location          | Description                                      |
|----------------------|-------------------|--------------------------------------------------|
| `apply_dilution()`   | calculation.py    | Corrects conductivities for dilution effect       |
| `split_strong()`     | calculation.py    | Finds split index for strong acid (min conductivity) |
| `split_weak()`       | calculation.py    | Finds split index for weak acid (max diff-delta)  |
| `_regression()`      | calculation.py    | Least-squares linear regression                   |
| `find_equivalence()` | calculation.py    | Full analysis pipeline (correct, split, regress, intersect, angle) |
| `calculate()`        | views.py          | API endpoint for titration analysis               |
| `download_input()`   | views.py          | CSV download for input data                       |
| `download_results()` | views.py          | CSV download for analysis results                 |

---

## Running Tests

Run the test suite to verify the calculation module:

```bash
python backend/manage.py test titration
```

To run a specific test case:

```bash
python backend/manage.py test titration.tests.TitrationCalculationTest.test_strong_acid_basic
```

---

## Deployment

### Option 1: Gunicorn (Linux)

1. Install Gunicorn:

```bash
pip install gunicorn
```

2. Run the server:

```bash
cd backend
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 4
```

### Option 2: Docker

Create a `Dockerfile` in the project root:

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn
COPY backend/ .
RUN python manage.py collectstatic --noinput 2>/dev/null || true
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

Build and run:

```bash
docker build -t titration-backend .
docker run -p 8000:8000 titration-backend
```

### Production Settings

Before deploying, update `config/settings.py`:

```python
DEBUG = False
ALLOWED_HOSTS = ["your-domain.com", "your-server-ip"]
CORS_ALLOWED_ORIGINS = ["https://your-frontend-domain.com"]
```

---

## Configuration Reference

| Setting                  | File           | Description                                  | Default         |
|-------------------------|----------------|----------------------------------------------|-----------------|
| DEBUG                   | settings.py    | Enable/disable debug mode                    | True            |
| ALLOWED_HOSTS           | settings.py    | List of allowed hostnames                    | ["*"]           |
| CORS_ALLOW_ALL_ORIGINS  | settings.py    | Allow all CORS origins (dev only)            | True            |
| CORS_ALLOWED_ORIGINS    | settings.py    | Whitelist of allowed CORS origins            | Not set         |
| SECRET_KEY              | settings.py    | Django secret key (change for production)    | Dev default     |
