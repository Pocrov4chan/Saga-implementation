import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models import Order
from saga.workflow import Step, Workflow
from saga.checkout import (
    charge_payment, refund_payment,
    reserve_inventory, release_inventory,
    schedule_shipping, cancel_shipping,
    checkout_steps,
)


def make_order() -> Order:
    return Order(user_id="u1", items=[{"name": "Widget", "qty": 1}], total_amount=50.0)


def ok_do(order, ctx):
    return {}


def ok_compensate(order, ctx):
    pass


def bomb_do(order, ctx):
    raise RuntimeError("boom")


def bomb_compensate(order, ctx):
    raise RuntimeError("compensation exploded")


class TestHappyPath:
    def test_result_is_ok(self):
        result = Workflow(checkout_steps()).run(make_order())
        assert result.ok

    def test_all_outcomes_succeeded(self):
        result = Workflow(checkout_steps()).run(make_order())
        assert all(o.succeeded for o in result.outcomes)

    def test_no_error(self):
        result = Workflow(checkout_steps()).run(make_order())
        assert result.error is None


class TestRollback:
    def test_second_fails_first_compensated(self):
        compensated = []
        def track(order, ctx):
            compensated.append("A")

        steps = [
            Step("A", ok_do, track),
            Step("B", bomb_do, ok_compensate),
        ]
        result = Workflow(steps).run(make_order())
        assert not result.ok
        assert "A" in compensated

    def test_third_fails_first_two_compensated(self):
        compensated = []
        def track(name):
            def _comp(order, ctx):
                compensated.append(name)
            return _comp

        steps = [
            Step("A", ok_do, track("A")),
            Step("B", ok_do, track("B")),
            Step("C", bomb_do, ok_compensate),
        ]
        Workflow(steps).run(make_order())
        assert compensated == ["B", "A"]

    def test_compensation_order_is_reversed(self):
        compensated = []
        def track(name):
            def _comp(order, ctx):
                compensated.append(name)
            return _comp

        steps = [
            Step("X", ok_do, track("X")),
            Step("Y", ok_do, track("Y")),
            Step("Z", ok_do, track("Z")),
            Step("boom", bomb_do, ok_compensate),
        ]
        Workflow(steps).run(make_order())
        assert compensated == ["Z", "Y", "X"]

    def test_compensation_failure_doesnt_stop_remaining(self):
        compensated = []
        def track(name):
            def _comp(order, ctx):
                compensated.append(name)
            return _comp

        steps = [
            Step("A", ok_do, track("A")),
            Step("B", ok_do, bomb_compensate),
            Step("C", bomb_do, ok_compensate),
        ]
        result = Workflow(steps).run(make_order())
        assert not result.ok
        assert "A" in compensated

    def test_failed_step_in_outcomes(self):
        steps = [
            Step("A", ok_do, ok_compensate),
            Step("B", bomb_do, ok_compensate),
        ]
        result = Workflow(steps).run(make_order())
        failed = next(o for o in result.outcomes if o.step_name == "B")
        assert not failed.succeeded
        assert failed.error == "boom"


class TestPayment:
    def test_charge_returns_transaction_id(self):
        data = charge_payment(make_order(), {})
        assert "transaction_id" in data
        assert data["amount"] == 50.0

    def test_refund_does_not_raise(self):
        ctx = {"payment": {"transaction_id": "txn_abc", "amount": 50.0}}
        refund_payment(make_order(), ctx)


class TestInventory:
    def test_reserve_returns_reservation(self):
        data = reserve_inventory(make_order(), {})
        assert "reservation_id" in data

    def test_release_does_not_raise(self):
        ctx = {"inventory": {"reservation_id": "res_abc", "items": []}}
        release_inventory(make_order(), ctx)


class TestShipping:
    def test_schedule_returns_shipment(self):
        data = schedule_shipping(make_order(), {})
        assert "shipment_id" in data

    def test_cancel_does_not_raise(self):
        ctx = {"shipping": {"shipment_id": "ship_abc"}}
        cancel_shipping(make_order(), ctx)
