from django.db import transaction
from django.core.management.base import BaseCommand
from images.models import FinnaSubjectPlace, \
                          FinnaImage, \
                          FinnaSubjectWikidataPlace
from django.db.models import Count
from images.locations import is_location_within_administrative_entity


class Command(BaseCommand):
    help = 'List all FinnaSubjectPlace rows without a wikidata_id value and FinnaImage instances with multiple subject places' # noqa

    def add_arguments(self, parser):

        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear best_wikidata_location values before listing results',
        )

        parser.add_argument(
            '--list_subject_places_without_wikidata_id',
            action='store_true',
            help='Only list FinnaSubjectPlace rows without a wikidata_id',
        )

    def list_subject_places_without_wikidata_id(self):
        # List FinnaSubjectPlace rows without wikidata_id
        obj = FinnaSubjectPlace.objects
        subject_places_without_wikidata = obj.filter(wikidata_id__isnull=True)
        if subject_places_without_wikidata.exists():
            self.stdout.write('FinnaSubjectPlace rows without wikidata_id:')
            for place in subject_places_without_wikidata:
                self.stdout.write(f'ID: {place.id}, Name: {place.name}')
        else:
            msg = 'No FinnaSubjectPlace rows without wikidata_id found.'
            self.stdout.write(msg)

    def get_best_location_id(self, wikidata_ids):
        print(wikidata_ids)
        if len(wikidata_ids) == 0:
            return None

        if len(wikidata_ids) == 1:
            return wikidata_ids[0]

        print("#")

        new_wikidata_ids = []
        for n in range(1, len(wikidata_ids)):
            place1 = wikidata_ids[n-1]
            place2 = wikidata_ids[n]
            if is_location_within_administrative_entity(place1, place2, True):
                new_wikidata_ids.append(place1)
            elif is_location_within_administrative_entity(place2,
                                                          place1,
                                                          True):
                new_wikidata_ids.append(place2)
            else:
                print(f'{place1} {place2}')
                return None

        print("*")
        if len(new_wikidata_ids) == 1:
            return new_wikidata_ids[0]

        if sorted(wikidata_ids) == sorted(new_wikidata_ids):
            print(wikidata_ids)
            return None

        return self.get_best_location_id(new_wikidata_ids)

    def handle(self, *args, **options):

        if options['clear']:
            # Clear all best_wikidata_location values
            self.stdout.write('Clearing all best_wikidata_location values...')
            for image in FinnaImage.objects.all():
                image.best_wikidata_location.clear()
            self.stdout.write('All best_wikidata_location values cleared.\n')
            return

        if options['list_subject_places_without_wikidata_id']:
            self.list_subject_places_without_wikidata_id()
            return

        with transaction.atomic():
            self.update_best_wikidata_location()

    def update_best_wikidata_location(self):
        base_uri = 'http://www.wikidata.org/entity/'

        # List FinnaImage instances with multiple subject places
        msg = '\nFinnaImage instances with multiple subject places:'
        self.stdout.write(msg)
        images_with_multiple_subject_places = FinnaImage.objects\
                                              .annotate(num_places=Count('subject_places'))\
                                              .filter(num_places__gt=1)\
                                              .filter(best_wikidata_location__isnull=True)
        if images_with_multiple_subject_places.exists():
            for image in images_with_multiple_subject_places:
                msg = f'\nFinnaImage ID: {image.id}, Finna ID: {image.finna_id}, Title: {image.title}'
                self.stdout.write(msg)
                print(image.finna_json_url)
                print(image.best_wikidata_location)
                wikidata_ids = set()
                for subject_place in image.subject_places.all():
                    wikidata_id = subject_place.wikidata_id.replace(base_uri, '')
                    wikidata_id = wikidata_id.replace("'", '')
                    wikidata_id = wikidata_id.replace("]", '')
                    wikidata_id = wikidata_id.replace("[", '')
                    print(f'* {subject_place}\t{wikidata_id}')
                    wikidata_ids.add(wikidata_id)

                wikidata_ids = list(wikidata_ids)
                wikidata_location_id = self.get_best_location_id(wikidata_ids)

                if wikidata_location_id:
                    obj = FinnaSubjectWikidataPlace.objects
                    print(wikidata_location_id)
                    uri = f'{base_uri}{wikidata_location_id}'
                    location, created = obj.get_or_create(uri=uri)
                    image.best_wikidata_location.add(location)
                    print(f'adding {uri}')
                    if '[' in uri:
                        print('2')
                        exit(1)

                    image.save()
                else:
                    print(f'No best location: {wikidata_ids}')
        else:
            msg = 'No FinnaImage instances with multiple subject places found.'
            self.stdout.write(msg)

        self.stdout.write('\nFinnaImage instances with exactly one subject place:')
        images_with_one_subject_place = FinnaImage.objects\
                                                  .annotate(num_places=Count('subject_places'))\
                                                  .filter(num_places=1)\
                                                  .filter(best_wikidata_location__isnull=True)
        if images_with_one_subject_place.exists():
            for image in images_with_one_subject_place:
                for subject_place in image.subject_places.all():
                    if subject_place.wikidata_id:
                        obj = FinnaSubjectWikidataPlace.objects
                        wikidata_id = subject_place.wikidata_id
                        wikidata_id = wikidata_id.replace(base_uri, '')
                        wikidata_id = wikidata_id.replace("'", '')
                        wikidata_id = wikidata_id.replace("]", '')
                        wikidata_id = wikidata_id.replace("[", '')

                        uri = f'{base_uri}{wikidata_id}'
                        if '[' in uri:
                            print(subject_place.wikidata_id)
                            print('1')
                            exit(1)
                        location, created = obj.get_or_create(uri=uri)
                        print(f'adding {uri}')
                        image.best_wikidata_location.add(location)
                        image.save()

                    else:
                        print(subject_place)
        else:
            msg = 'No FinnaImage instances with one subject place found.'
            self.stdout.write(msg)
