import uuid
from dataclasses import dataclass, field


@dataclass
class Order:
    order_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    user_id: str = ""
    items: list = field(default_factory=list)
    total_amount: float = 0.0
