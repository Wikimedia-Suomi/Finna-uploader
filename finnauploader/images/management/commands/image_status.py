from django.core.management.base import BaseCommand
from images.models import Image, ImageURL
import pywikibot
from pywikibot.data import sparql
import requests

class Command(BaseCommand):
    help = 'Print stats on images on database'

    def handle(self, *args, **kwargs):
        number_of_rows = Image.objects.count()
        print('Images')
        print(number_of_rows)

        images = Image.objects.filter(finna_id__isnull=True)
        print('Images without Finna_id')
        number_of_images=images.count()
        print(number_of_images)

        images = Image.objects.filter(finna_id_confirmed=False)
        print('Images without confirmed Finna_id')
        number_of_images=images.count()
        print(number_of_images)

        images = Image.objects.filter(finna_id_confirmed=True)
        print('Images with confirmed Finna_id')
        number_of_images=images.count()
        print(number_of_images)

        distinct_page_count = ImageURL.objects.filter(url__contains="fng.fi").values('image').distinct().count()
        print(distinct_page_count)


        self.stdout.write(self.style.SUCCESS(f'Images counted succesfully!'))
