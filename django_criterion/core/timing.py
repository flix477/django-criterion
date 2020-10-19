from dataclasses import dataclass
import math
from typing import Optional

from .result_type import ResultType


@dataclass(frozen=True)
class TimingDiff:
    average_diff: float
    negligible: bool

    def result_type(self) -> ResultType:
        if self.negligible:
            return ResultType.UNCHANGED
        return (
            ResultType.REGRESSION
            if self.average_diff > 0
            else ResultType.IMPROVEMENT
        )

    def pretty(self) -> str:
        return f"{self.average_diff:+.4f}"


@dataclass(frozen=True)
class Timing:
    average: float
    stdev: float
    variance: float
    diff: Optional[TimingDiff]

    def from_dict(d):
        return Timing(
            average=d["average"],
            stdev=d["stdev"],
            variance=d["variance"],
            diff=None,
        )

    def result_type(self) -> ResultType:
        return (
            ResultType.NO_PREVIOUS_DATA
            if self.diff is None
            else self.diff.result_type()
        )


F_TABLE_ALPHA = (0.01, 0.025, 0.05, 0.1)
F_TABLE = dict(
    (
        (4, (15.977, 9.6045, 6.3882, 4.10725)),
        (5, (10.967, 7.1464, 5.0503, 3.45298)),
        (6, (8.466, 5.8198, 4.2839, 3.05455)),
        (7, (6.993, 4.9949, 3.7870, 2.78493)),
        (8, (6.029, 4.4333, 3.4381, 2.58935)),
        (9, (5.351, 4.0260, 3.1789, 2.44034)),
        (10, (4.849, 3.7168, 2.9782, 2.32260)),
        (12, (4.155, 3.2773, 2.6866, 2.14744)),
        (15, (3.522, 2.8621, 2.4034, 1.97222)),
        (20, (2.938, 2.4645, 2.1242, 1.79384)),
        (24, (2.659, 2.2693, 1.9838, 1.70185)),
        (30, (2.386, 2.074, 1.8409, 1.60648)),
        (40, (2.114, 1.8750, 1.6928, 1.50562)),
        (60, (1.836, 1.667, 1.5343, 1.39520)),
        (120, (1.533, 1.433, 1.3519, 1.26457)),
    )
)


def linear_regression(p1, p2, x):
    a = (p2[1] - p1[1]) / (p2[0] - p1[0])
    b = p1[1] - a * p1[0]

    return a * x + b


def fcdf(f, freedom):
    table = F_TABLE[freedom]
    if f > table[0]:
        return 0.001
    elif f < table[-1]:
        return 0.2

    for i in range(0, len(table) - 1):
        down = i
        up = i + 1
        if table[down] >= f >= table[up]:
            return linear_regression(
                (table[down], F_TABLE_ALPHA[down]),
                (table[up], F_TABLE_ALPHA[up]),
                f,
            )

    raise Exception("Couldn't find an alpha value for F.")


INV_T_TABLE_FREEDOM = (8, 18, 25, 30, 60, 120)
INV_T_TABLE = dict(
    (
        (0.005, (3.355, 2.878, 2.787, 2.750, 2.660, 2.617)),
        (0.01, (2.896, 2.552, 2.485, 2.457, 2.390, 2.358)),
        (0.025, (2.306, 2.101, 2.060, 2.042, 2.000, 1.980)),
        (0.05, (1.860, 1.734, 1.708, 1.697, 1.671, 1.658)),
        (0.1, (1.397, 1.330, 1.316, 1.310, 1.296, 1.289)),
    )
)


def invt(a, freedom):
    table = INV_T_TABLE[a]
    for i in range(0, len(table) - 1):
        down = i
        up = i + 1
        if INV_T_TABLE_FREEDOM[down] <= freedom <= INV_T_TABLE_FREEDOM[up]:
            return linear_regression(
                (INV_T_TABLE_FREEDOM[down], table[down]),
                (INV_T_TABLE_FREEDOM[up], table[up]),
                freedom,
            )

    raise Exception("Couldn't find a t-value for freedom.")


def calc_timing_diff(new: Timing, old: Timing, n: int, a=0.05) -> TimingDiff:
    f = old.variance / new.variance
    if f >= 1:
        ap = 2 * fcdf(f, n - 1)
    else:
        ap = 2 * fcdf(1 / f, n - 1)

    if ap >= 0.2:
        sp = math.sqrt(
            ((n - 1) * old.variance + (n - 1) * new.variance) / (2 * n - 2)
        )
        t = (old.average - new.average) / (sp * math.sqrt(2 / n))
        t_value = invt(a, n * 2 - 2)
    else:
        v = ((old.variance / n + new.variance / n) ** 2) / (
            ((old.variance / n) ** 2) / (n - 1)
            + ((new.variance / n) ** 2) / (n - 1)
        )
        t = (old.average - new.average) / math.sqrt(
            (old.variance / n) + (new.variance / n)
        )
        t_value = invt(a / 2, v)

    reject = t >= t_value or t <= -t_value
    return TimingDiff(
        average_diff=new.average - old.average, negligible=(not reject)
    )
