# NetSentry

**Smart India Hackathon 2026 — Problem Statement 26155**  
**Team: Data_Sentinel**

NetSentry is an AI-Driven Multi-Vendor Network Security Compliance Auditor. It normalizes heterogeneous network configurations (Cisco, Juniper, Fortinet, Palo Alto, etc.) into a Canonical Security Baseline Model and evaluates them against CIS Benchmarks, NIST SP 800-53, DISA STIG, and ISO/IEC 27001 natively and deterministically.

---

## System Requirements

- **Python 3.10+** (Tested on Python 3.13)
- **Node.js 18+** and **npm**

---

## Setup Instructions

### Windows (One-Click Launchers)

1. **Start the Backend API Server**:
   ```cmd
   .\start_backend.bat
   ```
   *Automatically installs Python dependencies, sets the path, runs database migrations, and launches FastAPI on `http://127.0.0.1:8000`.*  
   *API Documentation (Swagger): `http://127.0.0.1:8000/docs`*

2. **Start the Frontend SOC Web App**:
   ```cmd
   .\start_frontend.bat
   ```
   *Automatically installs npm modules and launches the Vite dev server on `http://localhost:5173`.*

### Linux / macOS

1. **Start Backend**:
   ```bash
   chmod +x start_backend.sh start_frontend.sh
   ./start_backend.sh
   ```

2. **Start Frontend**:
   ```bash
   ./start_frontend.sh
   ```

---

## Manual Setup (Step-by-Step)

If you prefer to run the components manually without the scripts:

### 1. Backend Setup
```bash
python -m venv venv

# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r backend/requirements.txt

# Windows:
set PYTHONPATH=.     
# Linux/macOS: 
export PYTHONPATH="."

python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend Setup (in a separate terminal)
```bash
cd frontend
npm install
npm run dev
```

---

## Running Automated Tests

NetSentry includes a comprehensive suite of 69 automated unit and integration tests.

```bash
# Ensure PYTHONPATH is set to project root
# Windows (PowerShell):
$env:PYTHONPATH="."
python -m pytest backend/tests -v

# Linux / macOS:
export PYTHONPATH="."
python -m pytest backend/tests -v
```

### End-to-End Workflow Verification
To run the full end-to-end integration workflow demonstration:
```bash
python backend/tests/verify_e2e_flow.py
```
