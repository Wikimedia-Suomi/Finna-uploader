from django.core.management.base import BaseCommand
import time
from images.finna_record_api import get_supported_collections, \
                                    get_collection_name_from_alias, \
                                    get_collection_aliases
from images.import_helper import do_finna_import

class Command(BaseCommand):
    help = 'Import records from Finna search result to the database'

    # TODO: support for alias or institution:
    # Helsingin kaupunginmuseo and SA-kuva have institution but no collection information
    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument(
            '--collection',
            type=str,
            choices=get_supported_collections(),
            help=('Finna type argument. '
                  'Argument selects where lookfor matches.')
        )

        parser.add_argument(
            '--alias',
            type=str,
            choices=get_collection_aliases(),
            help=('Finna type argument. '
                  'Argument selects where lookfor matches.')
        )


        parser.add_argument(
            '--type',
            type=str,
            choices=['AllFields', 'Subjects'],
            help=('Finna type argument. '
                  'Argument selects where lookfor matches.')
        )

        parser.add_argument(
            '--lookfor',
            type=str,
            help='Finna lookfor argument.',
        )


    def handle(self, *args, **options):
        lookfor = options['lookfor'] or None
        type = options['type'] or None
        default_collection = 'Studio Kuvasiskojen kokoelma'
        collection = options['collection'] or default_collection
        aliascoll = options['alias'] or None

        if (aliascoll != None):
            collection = get_collection_name_from_alias(aliascoll)
        
        #if (collection == None and aliases != None):
        #    collection = aliases
        do_finna_import(lookfor, type, collection)

        self.stdout.write(self.style.SUCCESS('Images saved succesfully!'))
