import enum


class ResultType(enum.Enum):
    REGRESSION = "regression"
    IMPROVEMENT = "improvement"
    MIXED = "mixed"
    UNCHANGED = "unchanged"
    NO_PREVIOUS_DATA = "no-previous-data"

    def merge(self, other) -> "ResultType":
        if (self == ResultType.REGRESSION and other == ResultType.IMPROVEMENT) or (
            self == ResultType.IMPROVEMENT and other == ResultType.REGRESSION
        ):
            return ResultType.MIXED

        self_precendence = ResultType.PRECEDENCE.index(self)
        other_precendence = ResultType.PRECEDENCE.index(other)

        return self if self_precendence <= other_precendence else other

    def pretty_print(self) -> str:
        return ResultType.PRETTY[self]


ResultType.PRETTY = {
    ResultType.REGRESSION: "Regression",
    ResultType.IMPROVEMENT: "Improvement",
    ResultType.MIXED: "Mixed",
    ResultType.UNCHANGED: "Unchanged",
    ResultType.NO_PREVIOUS_DATA: "No previous data",
}

ResultType.PRECEDENCE = (
    ResultType.MIXED,
    ResultType.REGRESSION,
    ResultType.IMPROVEMENT,
    ResultType.UNCHANGED,
    ResultType.NO_PREVIOUS_DATA,
)
