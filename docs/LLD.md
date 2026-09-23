# AeroTwin AI — Low-Level Design (LLD)

**Document Reference**: `AEROTWIN-LLD-001`  
**Classification**: Software Component Design & Interface Specification  
**Status**: APPROVED BASELINE  

---

## 1. Domain Interfaces & Ports

All domain ports are strictly abstract base classes (`typing.Protocol` or `abc.ABC`) ensuring complete decoupling from infrastructure.

### 1.1 `ITelemetryProvider`
```python
from abc import ABC, abstractmethod
from typing import AsyncIterator
from app.domain.entities.telemetry import TelemetryFrame

class ITelemetryProvider(ABC):
    @abstractmethod
    async def stream_frames(self) -> AsyncIterator[TelemetryFrame]:
        """Asynchronously yield sequential telemetry frames."""
        pass

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to data feed."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Gracefully terminate feed."""
        pass
```

### 1.2 `ITelemetryRepository`
```python
from abc import ABC, abstractmethod
from typing import List, Optional
from app.domain.entities.telemetry import TelemetryFrame

class ITelemetryRepository(ABC):
    @abstractmethod
    async def save_frame(self, frame: TelemetryFrame) -> None:
        """Persist a single frame to storage."""
        pass

    @abstractmethod
    async def save_batch(self, frames: List[TelemetryFrame]) -> None:
        """Persist a batch of frames."""
        pass

    @abstractmethod
    async def get_flight_telemetry(self, mission_id: str, limit: int = 1000) -> List[TelemetryFrame]:
        """Retrieve historical telemetry for replay or analysis."""
        pass
```

### 1.3 `IAnomalyDetector` & `IFaultClassifier`
```python
from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any
from app.domain.value_objects.residuals import ResidualVector

class IAnomalyDetector(ABC):
    @abstractmethod
    def detect(self, residuals: ResidualVector) -> Tuple[bool, float]:
        """Returns (is_anomaly: bool, anomaly_score: float)."""
        pass

class IFaultClassifier(ABC):
    @abstractmethod
    def classify(self, residuals: ResidualVector) -> Tuple[str, float, Dict[str, float]]:
        """Returns (fault_label: str, confidence: float, class_probabilities: Dict[str, float])."""
        pass
```

---

## 2. Domain Entities & Value Objects

### 2.1 `TelemetryFrame`
```python
from pydantic import BaseModel, Field
from typing import List
from enum import Enum

class TelemetrySource(str, Enum):
    SIMULATED = "SIMULATED"
    REPLAY = "REPLAY"
    CAN_HARDWARE = "CAN_HARDWARE"

class QualityStatus(str, Enum):
    GOOD = "GOOD"
    DEGRADED = "DEGRADED"
    INVALID = "INVALID"

class TelemetryFrame(BaseModel):
    version: str = "1.0.0"
    timestamp: float = Field(..., gt=0.0)
    sequence_id: int = Field(..., ge=0)
    source_type: TelemetrySource = TelemetrySource.SIMULATED
    quality_flag: QualityStatus = QualityStatus.GOOD
    
    # Engine Operating Channels
    rpm: float = Field(..., ge=0.0, le=7000.0)
    manifold_pressure: float = Field(..., ge=5.0, le=55.0)
    throttle_position: float = Field(..., ge=0.0, le=100.0)
    fuel_flow: float = Field(..., ge=0.0, le=80.0)
    fuel_pressure: float = Field(..., ge=0.5, le=6.5)
    injection_timing: float = Field(..., ge=0.0, le=45.0)
    
    # Thermal Channels
    cht: List[float] = Field(..., min_length=4, max_length=4)
    egt: List[float] = Field(..., min_length=4, max_length=4)
    coolant_temp: float = Field(..., ge=-40.0, le=150.0)
    oil_temperature: float = Field(..., ge=-30.0, le=180.0)
    
    # Lubrication & Vibration
    oil_pressure: float = Field(..., ge=0.0, le=12.0)
    vibration_rms: float = Field(..., ge=0.0, le=20.0)
    
    # Avionics & Ambient
    battery_voltage: float = Field(..., ge=8.0, le=35.0)
    alternator_current: float = Field(..., ge=0.0, le=70.0)
    alternator_status: str = "OK"
    altitude: float = Field(..., ge=-500.0, le=15000.0)
    ambient_temp: float = Field(..., ge=-70.0, le=70.0)
    true_airspeed: float = Field(..., ge=0.0, le=150.0)
```

### 2.2 `ResidualVector`
```python
from pydantic import BaseModel
from typing import List

class ResidualVector(BaseModel):
    timestamp: float
    rpm_residual: float
    map_residual: float
    fuel_flow_residual: float
    cht_residuals: List[float]  # 4 cylinders
    egt_residuals: List[float]  # 4 cylinders
    oil_pressure_residual: float
    oil_temperature_residual: float
    vibration_residual: float

    def to_feature_array(self) -> List[float]:
        """Flattens residuals into numeric vector for ML inference."""
        return [
            self.rpm_residual,
            self.map_residual,
            self.fuel_flow_residual,
            *self.cht_residuals,
            *self.egt_residuals,
            self.oil_pressure_residual,
            self.oil_temperature_residual,
            self.vibration_residual,
        ]
```

---

## 3. Real-Time WebSocket Protocol

- **Endpoint**: `/ws/telemetry`
- **Rate**: 10 Hz
- **Payload Schema**:
```json
{
  "type": "TWIN_TELEMETRY_UPDATE",
  "data": {
    "actual": { ...TelemetryFrame... },
    "expected": { ...ExpectedFrame... },
    "residuals": { ...ResidualVector... },
    "diagnostics": {
      "anomaly_flag": false,
      "anomaly_score": 0.042,
      "fault_detected": "NORMAL_OPERATION",
      "fault_confidence": 0.985,
      "shap_attributions": {
        "cht_cyl3": 0.01,
        "oil_pressure": -0.02
      }
    },
    "health": {
      "overall_health_index": 97.4,
      "subsystems": {
        "combustion": 98.0,
        "lubrication": 96.5,
        "cooling": 97.8,
        "turbocharger": 99.1
      },
      "estimated_rul_hours": 1420.5
    }
  }
}
```
