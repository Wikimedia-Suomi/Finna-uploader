from django.core.management.base import BaseCommand
from images.models import Image, ImageURL, FinnaImage, FinnaCopyright, FinnaBuilding, FinnaNonPresenterAuthor, FinnaImageHash, FinnaImageHashURL
import pywikibot
from pywikibot.data import sparql
import requests
import time
from images.finna import do_finna_search
from images.imagehash_helpers import get_imagehashes, unsigned_to_signed, signed_to_unsigned

class Command(BaseCommand):
    help = 'Imagehash Finna images on database.'

    def process_finna_record(self, record):
        print(record)

    def handle(self, *args, **kwargs):
#        FinnaImageHashURL.objects.all().delete()
#        FinnaImageHash.objects.all().delete()

        photos=FinnaImage.objects.all()
        for photo in photos:
            if photo.number_of_images>1:
                print(photo)
                exit(1)

            print(photo.finna_id)
            index=0
            url=f'https://finna.fi/Cover/Show?source=Solr&id={photo.finna_id}&index={index}&size=large'
            i=get_imagehashes(url, thumbnail=True)
            print(i)

            imagehash, created=FinnaImageHash.objects.get_or_create(
                                  finna_image=photo, 
                                  phash=unsigned_to_signed(i['phash']), 
                                  dhash=unsigned_to_signed(i['dhash']),
                                  dhash_vertical=unsigned_to_signed(i['dhash_vertical'])
                               )
            if created:
                imagehash.save()

            imagehash_url, created=FinnaImageHashURL.objects.get_or_create(
                                       imagehash=imagehash, 
                                       url=url,
                                       width=i['width'],             
                                       height=i['height'],
                                       index=index,
                                       thumbnail=True
                                   )
            if created:
                imagehash_url.save()

            time.sleep(0.2)

        self.stdout.write(self.style.SUCCESS(f'Images counted succesfully!'))
