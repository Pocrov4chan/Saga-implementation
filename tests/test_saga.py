import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import Order, SagaStatus, StepStatus
from saga.orchestrator import SagaOrchestrator, SagaStep
from saga.steps import InventoryStep, PaymentStep, ShippingStep


def make_order() -> Order:
    return Order(
        user_id="user_1",
        items=[{"name": "Widget", "qty": 1}],
        total_amount=50.0,
    )


class BrokenCompensateStep(SagaStep):
    """Executes fine but throws during compensation."""

    def __init__(self, step_name: str):
        self._name = step_name

    @property
    def name(self) -> str:
        return self._name

    def execute(self, order, context):
        return {}

    def compensate(self, order, context):
        raise RuntimeError(f"{self._name} compensation exploded")


class OkStep(SagaStep):
    def __init__(self, step_name: str):
        self._name = step_name
        self.executed = False
        self.compensated = False

    @property
    def name(self) -> str:
        return self._name

    def execute(self, order, context):
        self.executed = True
        return {}

    def compensate(self, order, context):
        self.compensated = True


class FailStep(SagaStep):
    def __init__(self, step_name: str):
        self._name = step_name

    @property
    def name(self) -> str:
        return self._name

    def execute(self, order, context):
        raise RuntimeError(f"{self._name} failed")

    def compensate(self, order, context):
        pass


class TestHappyPath:
    def test_status_completed(self):
        result = SagaOrchestrator(
            [PaymentStep(), InventoryStep(), ShippingStep()]
        ).execute(make_order())
        assert result.status == SagaStatus.COMPLETED

    def test_all_steps_completed(self):
        result = SagaOrchestrator(
            [PaymentStep(), InventoryStep(), ShippingStep()]
        ).execute(make_order())
        assert all(sr.status == StepStatus.COMPLETED for sr in result.step_results)

    def test_no_error(self):
        result = SagaOrchestrator(
            [PaymentStep(), InventoryStep(), ShippingStep()]
        ).execute(make_order())
        assert result.error is None


class TestRollback:
    def test_second_step_fails_first_compensated(self):
        a = OkStep("A")
        result = SagaOrchestrator([a, FailStep("B")]).execute(make_order())
        assert result.status == SagaStatus.COMPENSATED
        assert a.compensated

    def test_third_step_fails_first_two_compensated(self):
        a, b = OkStep("A"), OkStep("B")
        SagaOrchestrator([a, b, FailStep("C")]).execute(make_order())
        assert a.compensated and b.compensated

    def test_compensation_order_is_reversed(self):
        log = []

        class Tracked(SagaStep):
            def __init__(self, n):
                self._name = n

            @property
            def name(self):
                return self._name

            def execute(self, order, context):
                return {}

            def compensate(self, order, context):
                log.append(self._name)

        SagaOrchestrator([Tracked("A"), Tracked("B"), FailStep("C")]).execute(
            make_order()
        )
        assert log == ["B", "A"]

    def test_compensation_failure_does_not_stop_remaining_rollback(self):
        a = OkStep("A")
        broken = BrokenCompensateStep("B")
        # C fails → rollback: B.compensate() throws, A.compensate() must still run
        result = SagaOrchestrator([a, broken, FailStep("C")]).execute(make_order())
        assert result.status == SagaStatus.COMPENSATED
        assert a.compensated  # A was still compensated despite B blowing up

    def test_failed_step_status_is_failed(self):
        result = SagaOrchestrator([OkStep("A"), FailStep("B")]).execute(make_order())
        failed = next(sr for sr in result.step_results if sr.step_name == "B")
        assert failed.status == StepStatus.FAILED


class TestPaymentStep:
    def test_execute_returns_transaction_id(self):
        data = PaymentStep().execute(make_order(), {})
        assert "transaction_id" in data
        assert data["amount"] == 50.0

    def test_execute_raises_on_failure(self):
        with pytest.raises(ValueError, match="Payment declined"):
            PaymentStep(should_fail=True).execute(make_order(), {})

    def test_compensate_does_not_raise(self):
        PaymentStep().compensate(
            make_order(), {"Payment": {"transaction_id": "txn_1", "amount": 50.0}}
        )


class TestInventoryStep:
    def test_execute_returns_reservation(self):
        data = InventoryStep().execute(make_order(), {})
        assert "reservation_id" in data

    def test_execute_raises_on_failure(self):
        with pytest.raises(ValueError, match="out of stock"):
            InventoryStep(should_fail=True).execute(make_order(), {})


class TestShippingStep:
    def test_execute_returns_shipment(self):
        data = ShippingStep().execute(make_order(), {})
        assert "shipment_id" in data

    def test_execute_raises_on_failure(self):
        with pytest.raises(ValueError, match="no delivery slots"):
            ShippingStep(should_fail=True).execute(make_order(), {})
