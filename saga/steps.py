import uuid

from models import Order
from saga.orchestrator import SagaStep


class PaymentStep(SagaStep):
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    @property
    def name(self) -> str:
        return "Payment"

    def execute(self, order: Order, context: dict) -> dict:
        if self.should_fail:
            raise ValueError("Payment declined: insufficient funds")
        return {
            "transaction_id": f"txn_{uuid.uuid4().hex[:8]}",
            "amount": order.total_amount,
        }

    def compensate(self, order: Order, context: dict) -> None:
        txn = context["Payment"]["transaction_id"]
        amount = context["Payment"]["amount"]
        print(f"refunding ${amount} for transaction {txn}")


class InventoryStep(SagaStep):
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    @property
    def name(self) -> str:
        return "Inventory"

    def execute(self, order: Order, context: dict) -> dict:
        if self.should_fail:
            raise ValueError(f"out of stock: {[i['name'] for i in order.items]}")
        reserved = [{"item": i["name"], "qty": i["qty"]} for i in order.items]
        return {"reservation_id": f"res_{uuid.uuid4().hex[:8]}", "items": reserved}

    def compensate(self, order: Order, context: dict) -> None:
        res_id = context["Inventory"]["reservation_id"]
        print(f"releasing reservation {res_id}")


class ShippingStep(SagaStep):
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    @property
    def name(self) -> str:
        return "Shipping"

    def execute(self, order: Order, context: dict) -> dict:
        if self.should_fail:
            raise ValueError("no delivery slots available")
        return {"shipment_id": f"ship_{uuid.uuid4().hex[:8]}", "carrier": "FastShip"}

    def compensate(self, order: Order, context: dict) -> None:
        shipment_id = context["Shipping"]["shipment_id"]
        print(f"cancelling shipment {shipment_id}")
