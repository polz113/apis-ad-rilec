from django.core.management.base import BaseCommand, CommandError
from apis_rilec.models import save_ldap


class Command(BaseCommand):
    help = "Backup data from ldap"

    def handle(self, *args, **options):
        save_ldap()

