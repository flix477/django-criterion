import contextlib
import dataclasses
from dataclasses import dataclass
from datetime import datetime
from importlib import import_module
import inspect
import json
import math
import random
import statistics
import sys
from time import perf_counter
from typing import Dict, TextIO, List

from django.conf import settings
from django.core.management.color import no_style
from django.db import connection, DEFAULT_DB_ALIAS
from django.core.management.sql import sql_flush
from django.test.utils import CaptureQueriesContext

from .timing import Timing, calc_timing_diff
from .queries import Queries
from .result_type import ResultType


@dataclass(frozen=True)
class BenchmarkResult:
    queries: Queries
    timing: Timing

    def from_dict(d):
        return BenchmarkResult(
            queries=Queries.from_dict(d["queries"]),
            timing=Timing.from_dict(d["timing"]),
        )

    def result_type(self) -> ResultType:
        return self.queries.result_type().merge(self.timing.result_type())


class BenchmarkCase:
    def setup(self):
        pass


def pure(f):
    """
    BenchmarkCase that do not modify the database can be declared pure
    with this annotation. This will speed up the test run by not flushing
    the database after the benchmark.
    """
    f.pure = True
    return f


@contextlib.contextmanager
def test_database():
    connection.creation.create_test_db()
    try:
        yield connection
    finally:
        connection.creation.destroy_test_db(DEFAULT_DB_ALIAS)


def get_cases(scripts: List[str]):
    cases = []
    for script in scripts:
        module = import_module(script)
        for name, value in inspect.getmembers(module):
            if (
                inspect.isclass(value)
                and issubclass(value, BenchmarkCase)
                and value != BenchmarkCase
            ):
                cases.append(value)

    return cases


def warmup_op(x: float, y: float) -> float:
    return math.sqrt((x / (y ** 2)) * (x + y))


def rand() -> float:
    return random.random() * 1000 + 10000


def warmup(for_seconds=10) -> None:
    t0 = datetime.now()

    while (datetime.now() - t0).seconds < for_seconds:
        warmup_op(rand(), rand())


def run_cases(cases, n: int) -> Dict[str, Dict[str, BenchmarkResult]]:
    return {qualified_name(x): run_case(x, n) for x in cases}


def run_case(case, n: int) -> Dict[str, BenchmarkResult]:
    case = case()

    return {
        name: run_bench(case, value, n)
        for name, value in inspect.getmembers(case)
        if inspect.ismethod(value) and name.startswith("bench_")
    }


def run_bench(case, f, sample_size) -> BenchmarkResult:
    total = 0
    timings = []
    is_pure = hasattr(f, "pure") and f.pure
    captured_queries = []

    for i in range(sample_size):
        case.setup()

        start = perf_counter()
        with CaptureQueriesContext(connection) as queries:
            f()

        timings.append(perf_counter() - start)
        total += len(queries.captured_queries)

        if not is_pure:
            flush(connection)
        if i == sample_size - 1:
            captured_queries = queries

    average_time = statistics.mean(timings)
    stdev = statistics.stdev(timings)
    variance = stdev ** 2

    return BenchmarkResult(
        queries=Queries(
            value=total / sample_size,
            captured_queries=captured_queries.captured_queries,
        ),
        timing=Timing(
            average=average_time, stdev=stdev, variance=variance, diff=None
        ),
    )


def flush(connection) -> None:
    sql_list = sql_flush(
        no_style(), connection, reset_sequences=True, allow_cascade=False
    )
    connection.ops.execute_sql_flush(settings.NAME, sql_list)


def qualified_name(c) -> str:
    return f"{c.__module__}.{c.__name__}"


def class_name(x: str) -> str:
    return x[x.rfind(".") + 1 :]  # noqa: E203


def load_results(f: TextIO) -> Dict[str, Dict[str, BenchmarkResult]]:
    try:
        results = json.load(f)
        return {
            case: {
                bench: BenchmarkResult.from_dict(bench_result)
                for bench, bench_result in benchmarks.items()
            }
            for case, benchmarks in results.items()
        }
    except Exception as error:
        print("ERROR: Couldn't load comparison data.")
        print(error)
        sys.exit(1)


def write_output(
    f: TextIO, data: Dict[str, Dict[str, BenchmarkResult]]
) -> None:
    try:
        json.dump(
            {
                case: {
                    bench: dataclasses.asdict(bench_result)
                    for bench, bench_result in benchmarks.items()
                }
                for case, benchmarks in data.items()
            },
            f,
        )
    except Exception as error:
        print("ERROR: Couldn't save benchmark data.")
        print(error)
        sys.exit(1)


def compare_results(
    a: Dict[str, Dict[str, BenchmarkResult]],
    b: Dict[str, Dict[str, BenchmarkResult]],
    n: int,
) -> Dict[str, Dict[str, BenchmarkResult]]:
    comparison = {}
    for case, benchmarks in a.items():
        if case not in b:
            comparison[case] = benchmarks
            continue

        benchmarks_b = b[case]
        comparison[case] = {}
        for bench_name, result in benchmarks.items():
            if bench_name not in benchmarks_b:
                comparison[case][bench_name] = result
                continue

            result_b = benchmarks_b[bench_name]
            queries = Queries(
                value=result.queries.value,
                diff=result.queries.value - result_b.queries.value,
                captured_queries=result.queries.captured_queries,
            )
            timing_diff = calc_timing_diff(result.timing, result_b.timing, n)
            timing = Timing(
                average=result.timing.average,
                stdev=result.timing.stdev,
                variance=result.timing.variance,
                diff=timing_diff,
            )
            comparison[case][bench_name] = BenchmarkResult(
                queries=queries, timing=timing
            )

    return comparison


def print_results(
    results: Dict[str, Dict[str, BenchmarkResult]], show_queries=False
) -> None:
    print("Results:")

    for case, results in results.items():
        print(f"- {class_name(case)}")
        for bench, result in results.items():
            result_type = result.result_type().pretty_print()
            print(f"  > {bench.ljust(30)}: {result_type}")
            queries = result.queries
            queries_result = queries.result_type().pretty_print()
            print(
                " " * 4
                + f"~ {'Number of queries'.ljust(28)}: {queries.value:.1f} ("
                + queries_result
                if queries.diff is None
                else (queries.pretty_diff() + ", " + queries_result) + ")"
            )

            if show_queries:
                for i, q in enumerate(queries.captured_queries):
                    print(" " * 6 + f"- Query {i + 1}:")
                    print(" " * 8 + f"> SQL: {q['sql']}")
                    print(" " * 8 + f"> Timing: {q['time']}")

            timing = result.timing
            timing_result = timing.result_type().pretty_print()
            print(
                " " * 4
                + f"~ {'Timing (seconds)'.ljust(28)}: "
                + f"{timing.average:.4f}±{timing.stdev:.4f} ("
                + timing_result
                if not timing.diff
                else timing.diff.pretty() + ", " + timing_result + ")"
            )


def run(
    scripts, output=None, compare=None, show_queries=False, sample_size=61
) -> None:
    if not scripts:
        # TODO: autodiscover
        scripts = []

    cases = get_cases(scripts)
    if not cases:
        print("Nothing to do.")
        sys.exit(0)

    with test_database():
        print("Warming up...")
        warmup()
        print("Running cases...")
        results = run_cases(cases, sample_size)

    if compare:
        with open(compare, "r") as f:
            comparison_data = load_results(f)
        results = compare_results(results, comparison_data, sample_size)

    print_results(results, show_queries=show_queries)

    if output:
        with open(output, "w") as f:
            write_output(f, results)

    count = len(results)
    print(f"Ran {count} case{'s' if count != 1 else ''}.")
