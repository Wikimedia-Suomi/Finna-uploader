from django.core.management.base import BaseCommand
from images.models import Image, ImageURL, FinnaImageHash, FinnaNonPresenterAuthor
import pywikibot
from pywikibot.data import sparql
import requests
from django.db.models import Count

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

        print("Imagehashes")
        t =  FinnaImageHash.objects.all().count()
        print(t)

        # this is not working in current model
        # Annotate each FinnaNonPresenterAuthor with the count of related FinnaImage instances
        # and order by the count in descending order
        #authors_with_image_count = FinnaNonPresenterAuthor.objects.annotate(
        #    image_count=Count('non_presenter_authors')
        #).order_by('-image_count')

        # not working in current model
        # Iterate over the queryset and print each author's name and their image count
        #for author in authors_with_image_count:
        #    print(f"{author.name}: {author.image_count} images")

        self.stdout.write(self.style.SUCCESS(f'Images counted succesfully!'))
