Here I implement Orchestration based Saga pattern for a multi-step checkout workflow

```
saga-checkout/
├── models.py            # Order dataclass
├── main.py              # demo scenarios
├── saga/
│   ├── workflow.py      # Step, Workflow, WorkflowResult
│   └── checkout.py      # payment/inventory/shipping functions
└── tests/
    └── test_saga.py
```

Steps are plain functions paired into a Step(name, action, rollback) dataclass, no inheritance needed.
The Workflow class runs them in sequence and rolls back on failure.

The workflow as following:

1. Client creates an Order and a list of Steps, each step is a pair of functions: action (do) and rollback (undo)

2. Workflow.run() goes through steps in order, calling each action(). The returned data gets stored in a shared context dict under the step name

3. If an action raises an exception, the workflow stops and iterates previously completed steps in reverse, calling their rollback()

4. Each rollback reads the context to know what to undo: refund the payment, release the reservation, cancel the shipment

5. If a rollback itself fails, the error is printed and the loop continues — remaining rollbacks still run

6. run() returns a WorkflowResult with ok=True/False, a list of outcomes per step, and the error message if any

Commands:
```
python3 -m venv .venv && source .venv/bin/activate
pip install pytest
python main.py        # runs 4 demo scenarios
pytest tests/ -v      # runs unit tests
```
