from abc import ABC, abstractmethod
from models import Order, SagaResult, StepResult, SagaStatus, StepStatus


class SagaStep(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def execute(self, order: Order, context: dict) -> dict:
        pass

    @abstractmethod
    def compensate(self, order: Order, context: dict) -> None:
        pass


class SagaOrchestrator:
    def __init__(self, steps: list[SagaStep]):
        self.steps = steps

    def execute(self, order: Order) -> SagaResult:
        result = SagaResult()
        context: dict = {}
        completed: list[SagaStep] = []

        for step in self.steps:
            print(f"{step.name}")
            try:
                data = step.execute(order, context)
                context[step.name] = data
                completed.append(step)
                result.step_results.append(StepResult(step.name, StepStatus.COMPLETED, data=data))
                print("Done")
            except Exception as e:
                print(f"{e}")
                result.step_results.append(StepResult(step.name, StepStatus.FAILED, error=str(e)))
                result.error = str(e)

                for s in reversed(completed):
                    print(f"compensating {s.name}")
                    try:
                        s.compensate(order, context)
                        for sr in result.step_results:
                            if sr.step_name == s.name:
                                sr.status = StepStatus.COMPENSATED
                        print("Done")
                    except Exception as ce:
                        print(f"compensation failed: {ce}")

                result.status = SagaStatus.COMPENSATED
                return result

        return result
