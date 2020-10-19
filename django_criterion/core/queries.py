from dataclasses import dataclass
from typing import Dict, List, Optional

from .result_type import ResultType


@dataclass(frozen=True)
class Queries:
    value: float
    captured_queries: List[Dict[str, str]]
    diff: Optional[float] = None

    def from_dict(d):
        return Queries(value=d["value"], diff=None, captured_queries=[])

    def pretty_diff(self) -> str:
        if self.diff is None:
            return "new"
        elif self.diff == 0:
            return "no change"

        return f"{self.diff:+.1f}"

    def result_type(self) -> ResultType:
        if self.diff is None:
            return ResultType.NO_PREVIOUS_DATA
        elif self.diff == 0:
            return ResultType.UNCHANGED
        elif self.diff > 0:
            return ResultType.REGRESSION

        return ResultType.IMPROVEMENT
