# AeroTwin AI — Setup & Installation Guide
**SIH26054 — Clean-Room Setup, Configuration, and Verification**

> [!IMPORTANT]
> **PROTOTYPE RESEARCH DISCLAIMER**  
> AeroTwin AI is an engineering research prototype developed for SIH26054 based on a generic 4-cylinder horizontally-opposed turbocharged aero-piston engine (Rotax 914/915 iS class). All scenarios, flight logs, fault injections, degradation rates, and mission profiles represent synthetic benchmark models. Not certified for flight operations.

---

## 1. System Requirements

### 1.1 Hardware Specifications
- **Processor:** 4-core x86_64 / ARM64 CPU ($\ge 2.0\text{ GHz}$)
- **RAM:** Minimum 8 GB (16 GB recommended for continuous soak runs)
- **Storage:** 2 GB free disk space
- **Graphics:** WebGL 2.0 compatible GPU / Integrated Graphics (Intel UHD 620+, Apple Silicon, NVIDIA GTX 1050+)
- **Display Resolution:** Optimized for $1920 \times 1080$ Full HD; responsive down to $1280 \times 720$

### 1.2 Software Prerequisites
- **Operating System:** Windows 10/11, Ubuntu 20.04/22.04 LTS, or macOS 12+
- **Python:** 3.10.x or 3.11.x (tested on Python 3.10.11)
- **Node.js:** Node.js 18.x or 20.x LTS
- **Package Managers:** `pip` ($\ge 23.0$), `npm` ($\ge 9.0$)
- **PowerShell:** Version 5.1+ (Windows native) or PowerShell Core (Cross-platform)

---

## 2. Clean-Room Installation Procedure

### 2.1 Clone Repository & Workspace Navigation
```bash
# Navigate to the repository root directory
cd d:/sih
```

### 2.2 Backend Environment Setup
```powershell
# 1. Navigate to the backend directory
cd backend

# 2. Create Python virtual environment
python -m venv .venv

# 3. Activate virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
# source .venv/bin/activate

# 4. Upgrade pip and core packaging tools
python -m pip install --upgrade pip setuptools wheel

# 5. Install all backend dependencies
pip install -r requirements.txt
```

### 2.3 Frontend Environment Setup
```powershell
# 1. Navigate to the frontend directory
cd ..\frontend

# 2. Install all Node.js npm packages
npm install
```

---

## 3. Configuration & Environment Variables

AeroTwin AI is configured via environment variables and fallback defaults. An example environment file is provided in `backend/.env.example`.

### 3.1 Backend Environment Configuration
Copy `backend/.env.example` to `backend/.env` (optional, defaults are fully operational out-of-the-box):
```bash
cp backend/.env.example backend/.env
```

Key configuration properties:
```ini
# Application Environment
AEROTWIN_ENV=development
AEROTWIN_DEBUG=true

# Server Networking
AEROTWIN_HOST=127.0.0.1
AEROTWIN_PORT=8000

# Telemetry Rates & Buffers
AEROTWIN_TELEMETRY_RATE_HZ=10
AEROTWIN_BUFFER_CAPACITY=1000
AEROTWIN_CLIENT_QUEUE_MAXSIZE=100

# Security Limits
AEROTWIN_MAX_MESSAGE_SIZE_BYTES=65536
```

---

## 4. Single-Command Startup

For automated demonstration startup on Windows, run the provided runner script:

```powershell
# From project root:
.\scripts\start_demo.ps1
```

The script automatically:
1. Validates the Python virtual environment and npm packages.
2. Checks port availability (Port 8000 and 5173).
3. Launches the FastAPI backend on `http://127.0.0.1:8000`.
4. Launches the Vite frontend development server on `http://localhost:5173`.
5. Probes `/api/v1/health` until healthy.
6. Handles graceful termination of both child processes upon entering `stop` or pressing `Ctrl+C`.

---

## 5. Manual Dual-Terminal Startup

Alternatively, launch backend and frontend services in separate terminals:

### Terminal 1 — Backend API & Telemetry Broadcaster:
```powershell
cd d:\sih\backend
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Terminal 2 — Frontend Digital Twin Station:
```powershell
cd d:\sih\frontend
npm run dev
```

---

## 6. Verification & System Health Checks

Once running, verify system endpoints:

| Endpoint | Target URL | Expected Response |
| :--- | :--- | :--- |
| **Cockpit UI** | `http://localhost:5173` | Visual Ground Station Cockpit |
| **System Health** | `http://localhost:8000/api/v1/health` | `{"status": "healthy"}` |
| **Subsystem Readiness** | `http://localhost:8000/api/v1/ready` | `{"status": "ready", "components": {...}}` |
| **Interactive API Docs** | `http://localhost:8000/docs` | Swagger UI documentation |
| **WebSocket Stream** | `ws://localhost:8000/api/v1/telemetry/ws` | Monotonic 10 Hz telemetry JSON stream |

---

## 7. Running the Full Test Suite

To verify complete repository integrity from a clean setup:

```powershell
# 1. Run all backend tests (Pytest)
cd d:\sih\backend
.\.venv\Scripts\pytest -v

# 2. Run architecture purity check
.\.venv\Scripts\pytest tests/unit/test_architecture_boundaries.py

# 3. Backend static analysis
.\.venv\Scripts\ruff check .
.\.venv\Scripts\ruff format --check .

# 4. Frontend tests (Vitest)
cd ..\frontend
npm test -- --run

# 5. Frontend static analysis & production build
npm run lint
npm run build
```
