from django.core.management.base import BaseCommand, CommandError
from apis_rilec.models import Datasource, apis_to_translations


class Command(BaseCommand):
    help = "Convert data from SAP/Studis to datasets"

    def handle(self, *args, **options):
        for i in DataSource.objects.filter(dataset=None):
            i.to_datasets()
        apis_to_translations()
        delete_old_userdata()
