# django-criterion

`django-criterion` is a Django admin command that allows you to benchmark Django code.
It gives you visibility on your database queries and timings in your application and on the impact of your modifications.


## Features

- Calculates timings and analyses queries
- Compares benchmark results and calculates a statistical significance test to determine if the difference is good, bad, or none.
- Produces JSON reports for easy processing


## Basic usage

1. Add `django_criterion` to your INSTALLED_APPS setting like this:
```
  INSTALLED_APPS = [
    ...
    'django_criterion'
  ]
```

2. Add benchmark cases in your project like this:
```
from django_criterion import BenchmarkCase


class MyBenchmarkCase(BenchmarkCase):
  def setup(self):
    # do things that you want to be executed everytime the case is ran
    pass

  def bench_my_benchmark(self):
    # do something that triggers database access to benchmark it
    # this method needs to have the 'bench_' prefix to be ran!
    pass

  def bench_something_else(self):
    # you can have as many as you want in a single benchmark case
    pass
```

3. Run your benchmarks: `./manage.py criterion`


## Advanced usage

### Command reference
```
./manage.py criterion [-ocq] ...BENCHMARK_CASES

Arguments:
  - BENCHMARK_CASES: list of module paths that have benchmark cases you want to run in them (example: project.api.users.benchmarks)

Flags:
  - -o OUTPUT_PATH: outputs a JSON report
  - -c PREVIOUS_OUTPUT_PATH: compares current results with a previous report
  - -q: prints every SQL query done within benchmarks, useful for analysing problems and finding cases of N+1 problems
```

### Pure benchmarks

If you have a benchmark that does not modify the database, like a GraphQL query, you will want to decorate it as `pure`. This is because django-criterion assumes by default that benchmarks will modify the database and so will always flush the database after running a benchmark, wasting a lot more time in the process.

You can decorate your benchmark as pure by doing this:

```
from django_criterion import BenchmarkCase, pure


class MyBenchmarkCase(BenchmarkCase):
  @pure
  def bench_my_pure_benchmark(self):
    # action with no side effects
    pass
```

### CI integration

You can integrate django-criterion into your CI pipeline, for example in pull requests to see a PR's impact on your benchmarks. We recommand using it as a tool to gain insight on how performance as changed, but not as a major job that refuses PRs in the case of regressions.


TODO: specific examples
