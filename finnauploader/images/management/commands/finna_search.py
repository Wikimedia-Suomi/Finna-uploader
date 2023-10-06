from django.core.management.base import BaseCommand
from images.models import Image, ImageURL, FinnaImage, FinnaCopyright, FinnaBuilding, FinnaNonPresenterAuthor
import pywikibot
from pywikibot.data import sparql
import requests
import time
from images.finna import do_finna_search

class Command(BaseCommand):
    help = 'Import records from Finna search result to the database'

    def process_finna_record(self, record):
         i=record['imageRights']
         copyright, created=FinnaCopyright.objects.get_or_create(copyright=i['copyright'], link=i['link'], description=i['description'])

         # created = True, False depending if the record was in the database already
         image,created=FinnaImage.objects.get_or_create(finna_id=record['id'], defaults={'copyright':copyright})

         # Update data if the record exists
         image.copyright=copyright

         if 'year' in record:
             image.year=record['year']

         image.title=record['title']

         # Save image metadata to db. Before this it is in memory only
         image.save()
       
         if 'buildings' in record:
             buildings=[]
             for building in record['buildings']:
                 finna_building, created=FinnaBuilding.objects.get_or_create(
                                   value=building['value'], 
                                   defaults={"translated": building['translated']}
                                )
                 image.buildings.add(finna_building)

         if 'nonPresenterAuthors' in record:
             for author in record['nonPresenterAuthors']:
                 finna_author, created=FinnaNonPresenterAuthor.objects.get_or_create(name=author['name'], role = author['role'])
                 image.non_presenter_authors.add(finna_author)

         print(f'{image} saved')
   
    def handle(self, *args, **kwargs):
        lookfor=None
        type=None
        collection='Studio Kuvasiskojen kokoelma'
       
        for page in range(1,101):
             # Prevent looping too fast for Finna server
             time.sleep(0.2)
             data=do_finna_search(page, lookfor, type, collection )
             if 'records' in data:
                 for record in data['records']:
                     self.process_finna_record(record)
             else:
                 break


        self.stdout.write(self.style.SUCCESS(f'Images counted succesfully!'))
