from models import Order
from saga.workflow import Step, Workflow
from saga.checkout import (
    charge_payment, refund_payment,
    reserve_inventory, release_inventory,
    schedule_shipping, cancel_shipping,
    checkout_steps,
)


def make_order() -> Order:
    return Order(
        user_id="user_42",
        items=[{"name": "Keyboard", "qty": 1}, {"name": "Mouse", "qty": 2}],
        total_amount=149.99,
    )


def failing_do(msg: str):
    def _fail(order, ctx):
        raise ValueError(msg)
    return _fail


if __name__ == "__main__":
    print("\n--- happy path ---")
    result = Workflow(checkout_steps()).run(make_order())
    print("ok: " + str(result.ok))
    assert result.ok

    print("\n--- inventory fails ---")
    steps = [
        Step("payment", charge_payment, refund_payment),
        Step("inventory", failing_do("out of stock"), release_inventory),
        Step("shipping", schedule_shipping, cancel_shipping),
    ]
    result = Workflow(steps).run(make_order())
    print("ok: " + str(result.ok) + ", error: " + str(result.error))
    assert not result.ok

    print("\n--- shipping fails ---")
    steps = [
        Step("payment", charge_payment, refund_payment),
        Step("inventory", reserve_inventory, release_inventory),
        Step("shipping", failing_do("no delivery slots"), cancel_shipping),
    ]
    result = Workflow(steps).run(make_order())
    print("ok: " + str(result.ok) + ", error: " + str(result.error))
    assert not result.ok

    print("\n--- payment fails ---")
    steps = [
        Step("payment", failing_do("insufficient funds"), refund_payment),
        Step("inventory", reserve_inventory, release_inventory),
        Step("shipping", schedule_shipping, cancel_shipping),
    ]
    result = Workflow(steps).run(make_order())
    print("ok: " + str(result.ok) + ", error: " + str(result.error))
    assert not result.ok

    print("\nall good.")
