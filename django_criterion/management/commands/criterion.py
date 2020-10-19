from django.core.management.base import BaseCommand

from django_criterion.core import run


class Command(BaseCommand):
    help = "Run benchmarks"

    def add_arguments(self, parser):
        parser.add_argument("scripts", nargs="*")
        parser.add_argument("-q", "--show-queries", action="store_true")
        parser.add_argument("-c", "--compare")
        parser.add_argument("-o", "--output")

    def handle(self, *args, scripts=[], output=None, compare=None, show_queries=False, **options):
        run(scripts, output=output, compare=compare, show_queries=show_queries)
