from django.core.management.base import BaseCommand, CommandError
import csv
from isisdata.models import *
from django.core.exceptions import ObjectDoesNotExist

class Command(BaseCommand):
    help = 'Adding NameAsEntered and DataDisplayOrder for ACRelations'

    def __init__(self, *args, **kwargs):
        self.failed = []
        return super(Command, self).__init__(*args, **kwargs)

    def add_arguments(self, parser):
        parser.add_argument('datapath', nargs=1, type=str)

    def handle(self, *args, **options):
        datapath = options['datapath'][0]

        with open(datapath, 'rU') as csvfile:
            filereader = csv.reader(csvfile, delimiter=',')
            for row in filereader:
                acr_id = row[0]
                name = row[1]
                order = row[2]

                try:
                    acrelation = ACRelation.objects.get(pk=acr_id)
                    if name:
                        acrelation.name_as_entered = name
                    if order:
                        acrelation.data_display_order = order
                    acrelation.save()
                except ObjectDoesNotExist:
                    print "Could not find object with id " + acr_id
