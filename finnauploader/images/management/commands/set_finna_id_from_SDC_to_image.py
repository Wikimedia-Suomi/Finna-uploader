from django.core.management.base import BaseCommand
from images.models import Image, ImageURL
from images.finna_record_api import get_finna_image_urls
from images.imagehash_helpers import compare_finna_hash
import pywikibot
from pywikibot.data import sparql
import requests

class Command(BaseCommand):
    help = 'Set Image.finna_id based on Finna_id from SDC'
    
    def is_matching_image(self, finna_id, commons_img_hash):

        #finna_record = get_finna_record(finna_id, True)
        finnaurls = get_finna_image_urls(finna_id)
        confirmed_finna_id = compare_finna_hash(finnaurls, commons_img_hash)
        if confirmed_finna_id:
            return True
        return False


    def handle(self, *args, **kwargs):
        site = pywikibot.Site("commons", "commons")  # for Wikimedia Commons
        site.login()

        images = Image.objects.filter(finna_id__isnull=True)
        number_of_images=images.count()
        print(f'Images to do {number_of_images}')

        for image in images:
            print(image.page_title)

            file_page = pywikibot.FilePage(site, page_title)
            commons_thumbnail_url = file_page.get_file_url(url_width=500)
            commons_img_hash = get_imagehashes(commons_thumbnail_url)

            # Quick copying from SDC to finna_id without confirmation
            print(image.sdc_finna_ids.count())
            if image.sdc_finna_ids.count() == 1:
                finna_id = image.sdc_finna_ids.first().finna_id
                print(finna_id)

                if (self.is_matching_image(finna_id, commons_img_hash) == True):
                    image.finna_id = finna_id
                    image.finna_id_confirmed = True
                    image.save()

            # If multiple values in SDC then confirm also
            elif image.sdc_finna_ids.count() > 1:

                for sdc_finna_id in image.sdc_finna_ids.all():

                    if (self.is_matching_image(sdc_finna_id, commons_img_hash) == True):
                        image.finna_id = sdc_finna_id
                        image.finna_id_confirmed = True
                        image.save()
                        break

        self.stdout.write(self.style.SUCCESS(f'Finna_ids updated successfully!'))
