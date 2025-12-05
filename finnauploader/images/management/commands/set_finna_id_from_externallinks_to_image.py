#

from django.core.management.base import BaseCommand
from images.models import Image, ImageURL
from images.finna_record_api import get_finna_id_from_url

from images.finna_record_api import get_finna_image_urls
from images.imagehash_helpers import compare_finna_hash

import pywikibot
from pywikibot.data import sparql
import requests

class Command(BaseCommand):
    help = 'Set Image.finna_id based on Finna_id from externallinks'
    
    # images might have been renamed in commons -> don't crash
    #
    def get_commons_image_hash(self, site, page_title):
        
        try:
            file_page = pywikibot.FilePage(site, page_title)
            commons_thumbnail_url = file_page.get_file_url(url_width=1000)
            commons_img_hash = get_imagehashes(commons_thumbnail_url)

            return commons_img_hash

        except:
        #except pywikibot.exceptions.NoPageError:
            #print("page missing from commons: ", page_title)
            print("error retrieving page from commons: ", page_title)
            return None
        return None
    
    def confirm_image_comparison(self, finna_id, commons_img_hash):
        if not finna_id:
            return None

        finnaurls = get_finna_image_urls(finna_id)
        
        return compare_finna_hash(finnaurls, commons_img_hash)

    def confirm_images(self, site):
        images = Image.objects.filter(finna_id__isnull=False)
        number_of_images=images.count()
        print(f'Images to do {number_of_images}')

        nro = 0
        total = len(images)

        for image in images:
            nro = nro +1
            print("Nro:", nro, "/", total, "title:", image.page_title)
            commons_image_hash = self.get_commons_image_hash(site, image.page_title)

            for url in image.urls.all():
                print(url.url)
                #finna_id=None
                
                finna_id = get_finna_id_from_url(url.url)
                confirmed_finna_id = self.confirm_image_comparison(finna_id, commons_image_hash)
                if confirmed_finna_id:
                    print("confirmed id: ", confirmed_finna_id, " old id: ", finna_id)
                    image.finna_id = confirmed_finna_id
                    image.finna_id_confirmed = True
                    image.save()
                    print("saving")
                    break
        

    def handle(self, *args, **kwargs):
        site = pywikibot.Site("commons", "commons")  # for Wikimedia Commons
        site.login()
        
        self.confirm_images(site)

        self.stdout.write(self.style.SUCCESS(f'Finna_ids updated successfully!'))
