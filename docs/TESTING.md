# AeroTwin AI — Testing & Verification Strategy

**Document Reference**: `AEROTWIN-TEST-001`  
**Classification**: QA / Test Governance  
**Status**: APPROVED BASELINE  

---

## 1. Quality Gate Philosophy

Every development phase must pass all automated verification checks before being presented for user review:
1. **Type Checking**: Strict TypeScript validation (`tsc --noEmit`) and MyPy checks.
2. **Linting & Formatting**: Ruff for backend (`ruff check`, `ruff format --check`); ESLint for frontend.
3. **Unit Tests**: Pytest for backend domain models and physics algorithms; Vitest for frontend components.
4. **Integration Tests**: WebSocket streaming checks, FastAPI route verification, SQLite/Parquet write/read tests.
5. **No False Completion**: Tests must assert concrete physical and mathematical behavior, not superficial dummy assertions.

---

## 2. Test Execution Commands

### Backend Verification
```powershell
# Run backend unit & integration tests
& "backend/.venv/Scripts/pytest.exe" backend/tests/ -v

# Run linting check
& "backend/.venv/Scripts/ruff.exe" check backend/

# Run format check
& "backend/.venv/Scripts/ruff.exe" format --check backend/
```

### Frontend Verification
```powershell
# Type checking
cd frontend; npm run build

# Unit & component tests
cd frontend; npm run test

# Linting
cd frontend; npm run lint
```
