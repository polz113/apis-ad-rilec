from django.core.management.base import BaseCommand, CommandError
from apis_rilec.models import MergedUserData, save_rilec,\
                              DataSource, apis_to_translations, delete_old_userdata,\
                              get_data_studis


class Command(BaseCommand):
    help = "Convert data from datasets to LDAPObjects"
    def add_arguments(self, parser):
        parser.add_argument('-gs', '--get_studis', action='store_true',
                            help="Get data from Studis")
        parser.add_argument('-cd', '--convert_datasets', action='store_true',
                            help="Convert SAP/Studis data to datasets")

    def handle(self, *args, **options):
        if options['get_studis']:
            get_data_studis()
        if options['convert_datasets']:
            for i in DataSource.objects.filter(dataset=None):
                i.to_datasets()
            apis_to_translations()
            delete_old_userdata()
        userdata = MergedUserData.objects.prefetch_related('data', 'data__fields', 'data__dataset__source').all()
        save_rilec(userdata)

