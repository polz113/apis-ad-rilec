from django.core.management.base import BaseCommand, CommandError
from apis_rilec.models import get_data_studis


class Command(BaseCommand):
    help = "Get data from Studis"

    def handle(self, *args, **options):
        get_data_studis()

