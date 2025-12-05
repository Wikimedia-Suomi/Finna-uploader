from django.core.management.base import BaseCommand
from images.models import Image, ImageURL
from images.finna_record_api import get_finna_record, is_valid_finna_record
import pywikibot
from pywikibot.data import sparql

class Command(BaseCommand):
    help = 'Updates Image.finna_id to latest finna_id from Finna.'

    def update_images(self, site):

        images = Image.objects.filter(finna_id__isnull=False, finna_id_confirmed=False)
        number_of_images=images.count()
        print(f'Images to do {number_of_images}')

        nro = 0
        total = len(images)
        seek='hkm.HKMS000005-km0000okvb'
        for image in images:
            nro = nro +1
            if seek and seek not in image.page_title:
                print(f'skip {image.finna_id}')
                continue
            seek=''
            if 'hkm.' in image.page_title:
                continue
            
            if not image.finna_id:
                print("no valid id in image, skipping:", image.page_title)
                continue

            print("Nro:", nro, "/", total, "title:", image.page_title)
            response = get_finna_record(image.finna_id)
            if (is_valid_finna_record(response) == True):
                new_finna_id = response['records'][0]['id']
                if image.finna_id != new_finna_id:
                    print("old id: ", image.finna_id, " new id: ", new_finna_id)
                    image.finna_id = new_finna_id
                    image.save()
            else:
                print(f'Virhe! {image.finna_id}') 

    def handle(self, *args, **kwargs):
        site = pywikibot.Site("commons", "commons")  # for Wikimedia Commons
        site.login()

        self.update_images(site)

        self.stdout.write(self.style.SUCCESS(f'Finna_ids updated successfully!'))
