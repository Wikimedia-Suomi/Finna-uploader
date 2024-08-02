from django.core.management.base import BaseCommand
from images.models import Image, ImageURL
from images.finna_record_api import get_finna_id_from_url
from images.imagehash_helpers import is_correct_finna_record
import pywikibot
from pywikibot.data import sparql
import requests

class Command(BaseCommand):
    help = 'Set Image.finna_id based on Finna_id from externallinks'

    def handle(self, *args, **kwargs):
        site = pywikibot.Site("commons", "commons")  # for Wikimedia Commons
        site.login()

        images = Image.objects.filter(finna_id__isnull=False)
        number_of_images=images.count()
        print(f'Images to do {number_of_images}')

        for image in images:
            print(image.page_title)
            finna_id=None

            for url in image.urls.all():
                print(url.url)
                finna_id=get_finna_id_from_url(url.url)
                if finna_id:
                    file_page = pywikibot.FilePage(site, image.page_title)
                    commons_thumbnail_url=file_page.get_file_url(url_width=1000)
                    confirmed_finna_id=is_correct_finna_record(finna_id, commons_thumbnail_url)
                    print(confirmed_finna_id)
                    if confirmed_finna_id:
                        image.finna_id = confirmed_finna_id
                        image.finna_id_confirmed = True
                        image.save()
                        print("saving")
                        break                

        self.stdout.write(self.style.SUCCESS(f'Finna_ids updated successfully!'))
