import uuid
from dataclasses import dataclass, field
from enum import Enum


class StepStatus(Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    COMPENSATED = "compensated"


class SagaStatus(Enum):
    COMPLETED = "completed"
    COMPENSATED = "compensated"


@dataclass
class Order:
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    items: list = field(default_factory=list)
    total_amount: float = 0.0


@dataclass
class StepResult:
    step_name: str
    status: StepStatus
    data: dict | None = None
    error: str | None = None


@dataclass
class SagaResult:
    status: SagaStatus = SagaStatus.COMPLETED
    step_results: list = field(default_factory=list)
    error: str | None = None
