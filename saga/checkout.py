import uuid
from models import Order
from saga.workflow import Step


def charge_payment(order: Order, ctx: dict) -> dict:
    txn_id = "txn_" + uuid.uuid4().hex[:8]
    print("  charged $" + str(order.total_amount) + ", transaction " + txn_id)
    return {"transaction_id": txn_id, "amount": order.total_amount}


def refund_payment(order: Order, ctx: dict) -> None:
    txn = ctx["payment"]["transaction_id"]
    amount = ctx["payment"]["amount"]
    print("  refunding $" + str(amount) + " for transaction " + txn)


def reserve_inventory(order: Order, ctx: dict) -> dict:
    res_id = "res_" + uuid.uuid4().hex[:8]
    reserved = [{"item": i["name"], "qty": i["qty"]} for i in order.items]
    print("  reserved " + str([r["item"] for r in reserved]) + ", reservation " + res_id)
    return {"reservation_id": res_id, "items": reserved}


def release_inventory(order: Order, ctx: dict) -> None:
    print("  releasing reservation " + ctx["inventory"]["reservation_id"])


def schedule_shipping(order: Order, ctx: dict) -> dict:
    ship_id = "ship_" + uuid.uuid4().hex[:8]
    print("  scheduled shipment " + ship_id)
    return {"shipment_id": ship_id, "carrier": "FastShip"}


def cancel_shipping(order: Order, ctx: dict) -> None:
    print("  cancelling shipment " + ctx["shipping"]["shipment_id"])


def checkout_steps() -> list[Step]:
    return [
        Step("payment", charge_payment, refund_payment),
        Step("inventory", reserve_inventory, release_inventory),
        Step("shipping", schedule_shipping, cancel_shipping),
    ]
