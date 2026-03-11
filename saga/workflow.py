from dataclasses import dataclass
from typing import Callable
from models import Order


@dataclass
class Step:
    name: str
    do: Callable[[Order, dict], dict]
    compensate: Callable[[Order, dict], None]


@dataclass
class StepOutcome:
    step_name: str
    succeeded: bool
    data: dict | None = None
    error: str | None = None


@dataclass
class WorkflowResult:
    ok: bool
    outcomes: list[StepOutcome]
    error: str | None = None


class Workflow:
    def __init__(self, steps: list[Step]):
        self.steps = steps

    def run(self, order: Order) -> WorkflowResult:
        context: dict = {}
        completed: list[Step] = []
        outcomes: list[StepOutcome] = []

        for step in self.steps:
            print(step.name)
            try:
                data = step.do(order, context)
                context[step.name] = data
                completed.append(step)
                outcomes.append(StepOutcome(step.name, succeeded=True, data=data))
                print("done")
            except Exception as e:
                print("failed: " + str(e))
                outcomes.append(StepOutcome(step.name, succeeded=False, error=str(e)))

                for prev in reversed(completed):
                    print("compensating " + prev.name)
                    try:
                        prev.compensate(order, context)
                        print("done")
                    except Exception as ce:
                        print("compensation failed: " + str(ce))

                return WorkflowResult(ok=False, outcomes=outcomes, error=str(e))

        return WorkflowResult(ok=True, outcomes=outcomes)
