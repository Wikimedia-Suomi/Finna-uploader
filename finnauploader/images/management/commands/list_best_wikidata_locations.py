from django.core.management.base import BaseCommand
from images.models import FinnaImage
import pywikibot
from pywikibot.data import sparql
import requests
from django.db.models import Count

class Command(BaseCommand):
    help = 'Print wikidata locations of images on database'

    def handle(self, *args, **kwargs):

        images=FinnaImage.objects.all().order_by('?')
        for image in images[:5]:
            print(image.url)
            print(image.title)
            for subject_place in image.subject_places.all():
                print(f'* {subject_place}')
            for wdlocation in image.best_wikidata_location.all():
                print(f'* {wdlocation}')
            print("\n\n")

        self.stdout.write(self.style.SUCCESS(f'Images counted succesfully!'))

