from django.core.management.base import BaseCommand
from images.models import Image, ImageURL, FinnaImage
import pywikibot
from pywikibot.data import sparql
import requests
import time
import json
from images.finna import do_finna_search
from images.serializer_helpers import finna_image_to_json
from images.finna_image_sdc_helpers import get_P7482_source_of_file_claim, \
                                           get_P275_licence_claim, \
                                           get_P6216_copyright_state_claim, \
                                           get_P9478_finna_id_claim, \
                                           get_P170_author_claims, \
                                           get_P195_collection_claims, \
                                           get_P180_subject_actors_claims, \
                                           get_P571_timestamp_claim
class Command(BaseCommand):
    help = 'Testing Finna record parsing and converting to SDC'

    def process_finna_record(self, data):
         r=FinnaImage.objects.create_from_data(data)
         print(finna_image_to_json(r))
         print('-----')
         print(r.url)
         print(r.finna_json)
         print('-----')

         c=get_P7482_source_of_file_claim(r)
         print(c)
         print('---')
         c=get_P275_licence_claim(r)
         print(c)
         print('---')

         c=get_P6216_copyright_state_claim(r)
         print(c)
         print('---')

         c=get_P9478_finna_id_claim(r)
         print(c)
         print('---')

         c=get_P170_author_claims(r)
         print(c)
         print('---')

         c=get_P195_collection_claims(r)
         print(c)
         print('---')

         c=get_P571_timestamp_claim(r)
         print(c)
         print('---')

         c=get_P180_subject_actors_claims(r)
         print(c)
         print('---')

#         s=FinnaImageSerializer(r)
#         print(r.toJSON())
         exit(1)

   
    def handle(self, *args, **kwargs):
        lookfor=None
        type=None
        collection='Studio Kuvasiskojen kokoelma'
#        collection='JOKA Journalistinen kuva-arkisto'
       
        for page in range(1,201):
             # Prevent looping too fast for Finna server
             time.sleep(1)
             data=do_finna_search(page, lookfor, type, collection )
             if 'records' in data:
                 for record in data['records']:
                     self.process_finna_record(record)
             else:
                 break


        self.stdout.write(self.style.SUCCESS(f'Images counted succesfully!'))
