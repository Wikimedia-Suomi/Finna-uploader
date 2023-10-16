from django.core.management.base import BaseCommand
from images.models import Image, ImageURL, FinnaImageHash, FinnaNonPresenterAuthor, FinnaCollection, FinnaSubjectPlace, FinnaSubjectActor, FinnaSubjectDetail
import pywikibot
from pywikibot.data import sparql
import requests
from django.db.models import Count

class Command(BaseCommand):
    help = 'Print stats on images on database'

    def handle(self, *args, **kwargs):

        # Annotate each FinnaNonPresenterAuthor with the count of related FinnaImage instances
        # and order by the count in descending order
        authors_with_image_count = FinnaNonPresenterAuthor.objects.annotate(
            image_count=Count('non_presenter_authors')
        ).order_by('-image_count')

        # Iterate over the queryset and print each author's name and their image count
        for author in authors_with_image_count:
            if author.image_count>10:
                print(f"{author.name}: {author.image_count} images")

        
        print("foo")
        t=FinnaSubjectDetail.objects.all()
        print(len(t))

        collections_with_image_count = FinnaCollection.objects.annotate(
            image_count=Count('collections')
        ).order_by('-image_count')

        for collection in collections_with_image_count:
            print(f"{collection.name}: {collection.image_count} images")



        subject_places_with_image_count = FinnaSubjectPlace.objects.annotate(
            image_count=Count('subject_places')
        ).order_by('-image_count')

        for subject_place in subject_places_with_image_count:
            if subject_place.image_count > 100:
                print(f"{subject_place.name}: {subject_place.image_count} images")

        print('----')

        subject_actors_with_image_count = FinnaSubjectActor.objects.annotate(
            image_count=Count('subject_actors')
        ).order_by('-image_count')

        for subject_actor in subject_actors_with_image_count:
            if subject_actor.image_count > 25:
                print(f"{subject_actor.name}: {subject_actor.image_count} images")

        print('----')

        subject_details_with_image_count = FinnaSubjectDetail.objects.annotate(
            image_count=Count('subject_details')
        ).order_by('-image_count')

        for subject_detail in subject_details_with_image_count:
            if subject_detail.image_count > 0:
                print(f"{subject_detail.name}: {subject_detail.image_count} images")

        self.stdout.write(self.style.SUCCESS(f'Images counted succesfully!'))

