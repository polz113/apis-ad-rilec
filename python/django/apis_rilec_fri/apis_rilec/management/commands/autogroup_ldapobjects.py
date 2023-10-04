from django.core.management.base import BaseCommand, CommandError
from apis_rilec.models import autogroup_ldapobjects()


class Command(BaseCommand):
    help = "Create autogroup LDAPObjects"

    def handle(self, *args, **options):
        autogroup_ldapobjects()
