from django.core.management.base import BaseCommand
from images.models import Image, ImageURL, FinnaImage, FinnaCopyright, FinnaBuilding, FinnaNonPresenterAuthor, FinnaSummary, FinnaSubject, FinnaSubjectPlace, FinnaSubjectActor, FinnaSubjectDetail, FinnaCollection
import pywikibot
from pywikibot.data import sparql
import requests
import time
from images.finna import do_finna_search

class Command(BaseCommand):
    help = 'Import records from Finna search result to the database'

    def process_finna_record(self, record):
#         if len(record['images'])>1:
#             print(record)
#             exit(1)
         i=record['imageRights']
         copyright, created=FinnaCopyright.objects.get_or_create(copyright=i['copyright'], link=i['link'], description=i['description'])

         # created = True, False depending if the record was in the database already
         image,created=FinnaImage.objects.get_or_create(finna_id=record['id'], defaults={'copyright':copyright})

         # Update data if the record exists
         image.copyright=copyright

         if 'year' in record:
             image.year=record['year']

         image.title=record['title']

         # One record can have multiple images
         image.number_of_images = len(record['images'])

         if 'identifierString' in record:
             image.identifier_string = record['identifierString']

         if 'shortTitle' in record:
             image.short_title = record['shortTitle']

         if 'summary' in record:
            image.summary, created=FinnaSummary.objects.get_or_create(name=record['summary'])

         if 'subjects' in record:
             for subject in record['subjects']:
                 finna_subject, created=FinnaSubject.objects.get_or_create(
                                   name=subject
                                )
                 image.subjects.add(finna_subject)

         if 'subjectPlaces' in record:
             for subject_place in record['subjectPlaces']:
                 finna_subject_place, created=FinnaSubjectPlace.objects.get_or_create(
                                   name=subject_place
                                )
                 image.subject_places.add(finna_subject_place)

         if 'subjectActors' in record:
             for subject_actor in record['subjectActors']:
                 finna_subject_actor, created=FinnaSubjectActor.objects.get_or_create(
                                   name=subject_actor
                                )
                 image.subject_actors.add(finna_subject_actor)

         if 'subjectDetails' in record:
             for subject_detail in record['subjectDetails']:
                 finna_subject_detail, created=FinnaSubjectDetail.objects.get_or_create(
                                   name=subject_detail
                                )
                 image.subject_details.add(finna_subject_detail)

         #if 'collections' in record:
             #for collection in record['collections']:
                 #finna_collection, created=FinnaCollection.objects.get_or_create(
                 #                  name=collection
                 #               )
                 #image.collections.add(finna_collection)

         # Save image metadata to db. Before this it is in memory only
         image.save()
       
         if 'buildings' in record:
             for building in record['buildings']:
                 finna_building, created=FinnaBuilding.objects.get_or_create(
                                   value=building['value'], 
                                   defaults={"translated": building['translated']}
                                )
                 image.buildings.add(finna_building)

         if 'nonPresenterAuthors' in record:
             for author in record['nonPresenterAuthors']:
                 finna_author, created=FinnaNonPresenterAuthor.objects.get_or_create(name=author['name'], role = author['role'])
                 image.non_presenter_authors.add(finna_author)

         print(f'{image} saved')
   
    def handle(self, *args, **kwargs):
        lookfor=None
        type=None
        collection='Studio Kuvasiskojen kokoelma'
#        collection='JOKA Journalistinen kuva-arkisto'
       
        for page in range(1,201):
             # Prevent looping too fast for Finna server
             time.sleep(0.2)
             data=do_finna_search(page, lookfor, type, collection )
             if 'records' in data:
                 for record in data['records']:
                     self.process_finna_record(record)
             else:
                 break


        self.stdout.write(self.style.SUCCESS(f'Images counted succesfully!'))
