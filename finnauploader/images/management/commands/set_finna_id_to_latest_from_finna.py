from django.core.management.base import BaseCommand
from images.models import Image, ImageURL
from images.finna_record_api import get_finna_id_from_url, get_finna_record
from images.imagehash_helpers import is_correct_finna_record
import pywikibot
from pywikibot.data import sparql

class Command(BaseCommand):
    help = 'Updates Image.finna_id to latest finna_id from Finna.'

    def handle(self, *args, **kwargs):
        site = pywikibot.Site("commons", "commons")  # for Wikimedia Commons
        site.login()

        images = Image.objects.filter(finna_id__isnull=False, finna_id_confirmed=False)
        number_of_images=images.count()
        print(f'Images to do {number_of_images}')

        seek='hkm.HKMS000005-km0000okvb'
        for image in images:
            if seek and seek not in image.page_title:
                print(f'skip {image.finna_id}')
                continue
            seek=''
            if 'hkm.' in image.page_title:
                continue
            print(image.page_title)
            response=get_finna_record(image.finna_id)
            if 'records' in response:
                record=response['records'][0]
                new_finna_id=record['id']
                if image.finna_id!=new_finna_id:
                    print(image.finna_id)
                    print(new_finna_id)
                    image.finna_id=new_finna_id
                    image.save()
            else:
                print(f'Virhe! {image.finna_id}') 


        self.stdout.write(self.style.SUCCESS(f'Finna_ids updated successfully!'))
