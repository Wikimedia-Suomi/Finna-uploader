from django.core.management.base import BaseCommand
from images.models import Image, ImageURL, FinnaImage, FinnaCopyright, FinnaBuilding, FinnaNonPresenterAuthor, FinnaImageHash, FinnaImageHashURL
import pywikibot
from pywikibot.data import sparql
import requests
import time
from images.finna import do_finna_search
from images.imagehash_helpers import get_imagehashes
from images.conversion import unsigned_to_signed, signed_to_unsigned

class Command(BaseCommand):
    help = 'Imagehash Finna images on database.'

    def process_finna_record(self, record):
        print(record)

    def handle(self, *args, **kwargs):
#        FinnaImageHashURL.objects.all().delete()
#        FinnaImageHash.objects.all().delete()

        photos=FinnaImage.objects.all()
        for photo in photos:
            imagehash=FinnaImageHash.objects.filter(finna_image=photo).first()

            for index in range(photo.number_of_images):
                imagehash_url=FinnaImageHashURL.objects.filter(imagehash=imagehash, index=index).first()
                if imagehash_url:
                    print(f'skipping: {photo.finna_id} {index}')
                    continue

                url=f'https://finna.fi/Cover/Show?source=Solr&id={photo.finna_id}&index={index}&size=large'
                print(photo.title)
                print(photo.copyright.copyright)
                print(url)

                try:
                    i=get_imagehashes(url, thumbnail=True)
                except:
                    continue

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
