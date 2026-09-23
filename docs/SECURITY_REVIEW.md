# AeroTwin AI — Phase 9 Security Review Report
## SIH26054 — Input Validation, Storage Defenses, and Security Posture

> **PROTOTYPE DISCLAIMER**: AeroTwin AI is an engineering research prototype. Security review is focused on local prototype defense-in-depth, input boundary validation, storage containment, and safe API execution. It is not evaluated against certified aerospace RTCA DO-326A / ED-202A cyber-security airworthiness standards.

---

### 1. Security Analysis Overview

Phase 9 performed an exhaustive security review of the AeroTwin AI software stack across four dimensions:
1. **Dynamic Execution & Code Injection Hazards**: AST scanning for dangerous built-in execution functions.
2. **File System & Storage Path Traversal**: Audit of file resolution in historical replay and mission export layers.
3. **Network & Protocol Input Fuzzing**: Boundary condition testing on REST and WebSocket ingress points.
4. **Secrets & Sensitive Information Hygiene**: Verification of repo configuration, environment files, and logging.

---

### 2. AST Static Code Security Audit

A full AST audit was executed across all Python files in the application codebase (`app/`):
- `eval()` occurrences: **0**
- `exec()` occurrences: **0**
- `os.system()` occurrences: **0**
- `subprocess` with `shell=True`: **0**
- `pickle.loads()` / `pickle.load()` occurrences: **0**
- Arbitrary code deserialization: **0** (Model loading uses `joblib.load()` strictly pointing to configured, local files in `models/`).

### 3. Path Traversal Defense Verification

#### 3.1 Defense-in-Depth Architecture
In historical replay and flight log access, user-supplied dataset names could theoretically attempt relative directory escape (`../../`). AeroTwin AI enforces two independent containment layers:

1. **Filename Sanitization**:
   ```python
   clean_name = Path(filename).name
   ```
   `Path.name` strips directory components (`../`, `..\`, absolute root slashes), preventing relative path traversal.

2. **Containment Anchor Verification**:
   ```python
   target = (search_dir / clean_name).resolve()
   if not target.is_relative_to(search_dir.resolve()) or not target.is_file():
       raise FileNotFoundError("Dataset not found in authorized storage locations.")
   ```
   Ensures that resolved path is strictly a descendant of the authorized search directory.

#### 3.2 Automated Penetration Testing
Tested attack vectors against `ReplayService.resolve_dataset_path` and REST API endpoints (`/api/v1/replay/load`, `/api/v1/replay/metadata`):
- `../../../../../../../../etc/passwd` $\to$ Rejected (404/FileNotFoundError).
- `..\\..\\Windows\\System32\\cmd.exe` $\to$ Rejected (404/FileNotFoundError).
- `/etc/shadow` $\to$ Rejected (404/FileNotFoundError).
- `C:\\Windows\\win.ini` $\to$ Rejected (404/FileNotFoundError).
- Null byte injections (`%00`) $\to$ Rejected (422/ValidationError).

### 4. Injection & Adversarial Payload Safety

1. **SQL Injection Defense**:
   - Telemetry queries in `TelemetryRepository` use parameterized SQL statements (`?` placeholders).
   - Replay loader table creation and querying uses parameterized queries or structured DataFrame readers.
   - Tested injection string `test'; DROP TABLE telemetry_frames; --.sqlite`: safely treated as a literal file path; 0 SQL commands executed.

2. **WebSocket Command Defense**:
   - `RealtimeTelemetryService.execute_command()` strictly validates command verbs and parameter types.
   - Unrecognized commands log warnings without raising exceptions or destabilizing active connections.
   - Non-scalar parameters for scalar inputs (e.g. lists for scenario strings) are rejected safely.

3. **Numerical Adversarial Input Defense**:
   - Non-finite floating point inputs (`float("nan")`, `float("inf")`, `-float("inf")`) are intercepted by `TelemetryValidator.validate()`.
   - Resulting frames are marked `QualityStatus.INVALID`, logged, and isolated from analytical calculation.
   - Pydantic models dump strictly valid RFC 8259 JSON (`allow_nan=False` verified), preventing JavaScript `JSON.parse` failures on the frontend.

### 5. Secrets Hygiene & Configuration

- Git Repository: `.env` is listed in `.gitignore` and has never been committed.
- Configuration Templates: `.env.example` contains only non-sensitive placeholder tokens.
- Error Handling: REST exceptions return structured JSON error envelopes with sanitized client messages, avoiding stack trace disclosure in production configurations.
