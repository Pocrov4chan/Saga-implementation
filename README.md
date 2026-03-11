# Saga Pattern — E-Commerce Checkout

A Python implementation of the **Orchestration Saga** pattern for a multi-step checkout workflow.

## What is the Saga Pattern?

A saga is a sequence of local transactions where each step publishes an event or triggers the next step. If any step fails, the saga executes **compensating transactions** in reverse order to undo all previously completed work — restoring the system to a consistent state without distributed locks or two-phase commit.

This implementation uses the **orchestration** variant: a central `SagaOrchestrator` controls the sequence and knows when to roll back.

---

## Design

### Core idea

```
execute:   Payment → Inventory → Shipping
                                     ↓ fails
compensate:             Inventory ← Shipping (skipped, never ran)
compensate: Payment ← Inventory
```

Each step exposes two operations:

| Method | Purpose |
|---|---|
| `execute(order, context)` | Perform the action; raise an exception to signal failure |
| `compensate(order, context)` | Undo the action; must not raise |

The `context` dict carries output data between steps (e.g., `transaction_id` from Payment is available to all subsequent steps and compensations).

### Files

```
saga-checkout/
├── models.py              # Order, StepResult, SagaResult, status enums
├── saga/
│   ├── orchestrator.py    # SagaStep (ABC) + SagaOrchestrator (generic runner)
│   └── steps.py           # PaymentStep, InventoryStep, ShippingStep
├── main.py                # Runnable demo: 4 scenarios
└── tests/
    └── test_saga.py       # 16 unit tests covering happy path and rollback
```

### Checkout steps

| Step | execute | compensate |
|---|---|---|
| **Payment** | Charges the customer, returns `transaction_id` | Refunds the charge |
| **Inventory** | Reserves items, returns `reservation_id` | Releases the reservation |
| **Shipping** | Creates a shipment, returns `shipment_id` | Cancels the shipment |

---

## Running the demo

```bash
python3 -m venv .venv && source .venv/bin/activate
python main.py
```

Four scenarios are demonstrated:
1. **Happy path** — all three steps succeed
2. **Inventory fails** — payment is refunded
3. **Shipping fails** — inventory reservation released, then payment refunded
4. **Payment fails** — nothing to roll back

## Running the tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

16 tests covering:
- Happy path completion and step count
- Rollback triggered at each position (step 1, 2, 3)
- Compensation order is strictly reversed
- Failed step itself is not marked as compensated
- Each step's execute/compensate contract

---

## Key design decisions

**Generic orchestrator, not hardcoded checkout.** `SagaOrchestrator` takes any list of `SagaStep` objects. Adding a new step (e.g., `NotificationStep`) requires no changes to the orchestrator — only a new class implementing the two-method interface.

**Context dict for step communication.** Each `execute` return value is stored in `context[step.name]`. Compensations read from context to know what to undo (e.g., which transaction ID to refund). This avoids storing saga state externally.

**Compensation failures are logged, not re-raised.** A compensation that throws would leave the rollback loop in an inconsistent state. Logging the failure and continuing is the safer trade-off — partial rollback is better than a broken rollback.

**No external dependencies.** The implementation is pure Python stdlib. No message queues, databases, or Docker required — the pattern itself is the focus.
