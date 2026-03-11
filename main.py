from models import Order, SagaStatus
from saga.orchestrator import SagaOrchestrator, SagaStep
from saga.steps import PaymentStep, InventoryStep, ShippingStep


def make_order() -> Order:
    return Order(
        user_id="user_42",
        items=[{"name": "Keyboard", "qty": 1}, {"name": "Mouse", "qty": 2}],
        total_amount=149.99,
    )


def run(title: str, steps: list[SagaStep], expected_status: SagaStatus) -> None:
    print(f"\n--- {title} ---")
    result = SagaOrchestrator(steps).execute(make_order())
    print(f"result: {result.status.value}")
    if result.error:
        print(f"error:  {result.error}")
    assert result.status == expected_status


if __name__ == "__main__":
    run("Happy path", [PaymentStep(), InventoryStep(), ShippingStep()], SagaStatus.COMPLETED)
    run("Inventory fails", [PaymentStep(), InventoryStep(should_fail=True), ShippingStep()], SagaStatus.COMPENSATED)
    run("Shipping fails", [PaymentStep(), InventoryStep(), ShippingStep(should_fail=True)], SagaStatus.COMPENSATED)
    run("Payment fails", [PaymentStep(should_fail=True), InventoryStep(), ShippingStep()], SagaStatus.COMPENSATED)
    print("\nall good.")
