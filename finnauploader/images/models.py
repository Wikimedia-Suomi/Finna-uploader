from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from images.finna import get_finna_record_url

# Create your models here.


# Commons image
class Image(models.Model):
    page_id = models.PositiveIntegerField(unique=True)
    page_title = models.CharField(max_length=200)
    finna_id = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    finna_id_confirmed = models.BooleanField(default=False)
    finna_id_confirmed_at = models.DateTimeField(null=True, blank=True)


# Commons external links linked from image
class ImageURL(models.Model):
    image = models.ForeignKey(Image, related_name="urls", on_delete=models.CASCADE)
    url = models.URLField(max_length=500)

    class Meta:
        unique_together = [['image', 'url']]


# Commons external links linked from image
class SdcFinnaID(models.Model):
    image = models.ForeignKey(Image, related_name="sdc_finna_ids", on_delete=models.CASCADE)
    finna_id = models.CharField(max_length=200, db_index=True)

    class Meta:
        unique_together = [['image', 'finna_id']]


class FinnaBuilding(models.Model):
    value = models.CharField(max_length=64)
    translated = models.CharField(max_length=64)

    def __str__(self):
        return self.translated


class FinnaImageRight(models.Model):
    copyright = models.CharField(max_length=32)
    link = models.URLField(max_length=500)
    description = models.TextField()

    def __str__(self):
        return self.copyright


class FinnaNonPresenterAuthor(models.Model):
    name = models.CharField(max_length=64)
    role = models.CharField(max_length=64)

    def __str__(self):
        return self.name


class FinnaSummary(models.Model):
    text = models.TextField()

    def __str__(self):
        return self.name


class FinnaSubject(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class FinnaSubjectPlace(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class FinnaSubjectActor(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class FinnaSubjectDetail(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class FinnaCollection(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class FinnaInstitution(models.Model):
    value = models.CharField(max_length=200)
    translated = models.CharField(max_length=200)

    def __str__(self):
        return self.value

# Managers

class FinnaRecordManager(models.Manager):

    # Second try to make this readable
    def create_from_finna_record(self, record):

        # copyright tag is mandatory information so it is added on creation
        i = record['imageRights']
        image_right, created = FinnaImageRight.objects.get_or_create(copyright=i['copyright'],
                                                                     link=i['link'],
                                                                     description=i['description'])

        # created = True, False depending if the record was in the database already
        image, created = FinnaImage.objects.get_or_create(finna_id=record['id'],
                                                          defaults={'image_right': image_right})

        image.title = record['title']
        image.short_title = record['shortTitle']
        image.image_right = image_right
        image.number_of_images = len(record['images'])
        image.year = record.pop('year', None)
        image.identifier_string = record.pop('identifierString', None)
        image.measurements = record.pop('measurements', None)

        # Extract imagesExtended data
        images_extended_data = record.pop('imagesExtended', None)
        if images_extended_data:
            image.master_url = images_extended_data[0]['highResolution']['original'][0]['url']
            image.master_format = images_extended_data[0]['highResolution']['original'][0]['format']
        else:
            print("Error: imagesExtended missing")
            exit(1)

        # Extract date string from events
        events = record.pop('events', None)
        if events:
            valmistus = record.pop('valmistus', None)
            if valmistus:
                image.date_string=valmistus[0]['date']

        # Data which is stored to separate tables

        if 'summary' in record:
            image.summary, created = FinnaSummary.objects.get_or_create(text=record['summary'])

        if 'subjects' in record:
            obj = FinnaSubject.objects
            for subject in record['subjects']:
                finna_subject, created = obj.get_or_create(name=subject)
                image.subjects.add(finna_subject)

        if 'subjectPlaces' in record:
            obj = FinnaSubjectPlace.objects
            for subject in record['subjectPlaces']:
                finna_subject, created = obj.get_or_create(name=subject)
                image.subject_places.add(finna_subject)

        if 'subjectActors' in record:
            obj = FinnaSubjectActor.objects
            for subject in record['subjectActors']:
                finna_subject, created = obj.get_or_create(name=subject)
                image.subject_actors.add(finna_subject)

        if 'subjectDetails' in record:
            obj = FinnaSubjectDetail.objects
            for subject in record['subjectDetails']:
                finna_subject, created = obj.get_or_create(name=subject)
                image.subject_details.add(finna_subject)

        if 'collections' in record:
            obj = FinnaCollection.objects
            for collection in record['collections']:
                finna_collection, created = obj.get_or_create(name=collection)
                image.collections.add(finna_collection)

        if 'buildings' in record:
            obj = FinnaBuilding.objects
            for building in record['buildings']:
                value = building['value']
                defaults = {"translated": building['translated']}
                finna_building, created = obj.get_or_create(value=value, defaults=defaults)
                image.buildings.add(finna_building)

        if 'institutions' in record:
            obj = FinnaInstitution.objects
            for institution in record['institutions']:
                value = institution['value']
                defaults = {"translated": institution['translated']}
                finna_institution, created = obj.get_or_create(
                                   value=value,
                                   defaults=defaults
                                )
                image.institutions.add(finna_institution)

        if 'nonPresenterAuthors' in record:
            obj = FinnaNonPresenterAuthor.objects
            for author in record['nonPresenterAuthors']:
                name = author['name']
                role = author['role']
                finna_author, created = obj.get_or_create(name=name, role=role)
                image.non_presenter_authors.add(finna_author)

        image.save()
        return image

    # First try 
    def create_from_data(self, data):

        # Extract and handle non_presenter_authors data
        non_presenter_authors_data = data.pop('nonPresenterAuthors', [])
        non_presenter_authors = []
        for non_presenter_author_data in non_presenter_authors_data:
            author = FinnaNonPresenterAuthor.objects.get_or_create(
                name=non_presenter_author_data['name'],
                role=non_presenter_author_data['role']
                )[0]
            non_presenter_authors.append(author)

        # Extract and handle buildings data
        buildings_data = data.pop('buildings', [])
        buildings = [FinnaBuilding.objects.get_or_create(value=building_data['value'], defaults={'translated': building_data['translated']})[0] for building_data in buildings_data]

        # Extract and handle subjects data
        subjects_data = data.pop('subjects', [])
        subjects = [FinnaSubject.objects.get_or_create(name=subject_name)[0] for subject_name in subjects_data]

        # Extract and handle subjectPlaces data
        subject_places_data = data.pop('subjectPlaces', [])
        subject_places = [FinnaSubjectPlace.objects.get_or_create(name=subject_place_name)[0] for subject_place_name in subject_places_data]

        # Extract and handle subjectActors data
        subject_actors_data = data.pop('subjectActors', [])
        subject_actors = [FinnaSubjectActor.objects.get_or_create(name=subject_actor_name)[0] for subject_actor_name in subject_actors_data]

        # Extract and handle subjectDetails data
        subject_details_data = data.pop('subjectDetails', [])
        subject_details = [FinnaSubjectDetail.objects.get_or_create(name=subject_detail_name)[0] for subject_detail_name in subject_details_data]

        # Extract and handle collections data
        collections_data = data.pop('collections', [])
        collections = [FinnaCollection.objects.get_or_create(name=collection_name)[0] for collection_name in collections_data]

        # Extract and handle institutions data
        institutions_data = data.pop('institutions', [])
        institutions = [FinnaInstitution.objects.get_or_create(value=institution_data['value'], defaults={'translated': institution_data['translated']})[0] for institution_data in institutions_data]

        # Extract and handle image_right data
        image_rights_data = data.pop('imageRights', {})
        image_rights = FinnaImageRight.objects.get_or_create(copyright=image_rights_data['copyright'], link=image_rights_data['link'], description=image_rights_data['description'][0])[0]

        # Extract images data
        images_data = data.pop('images', [])

        # Extract imagesExtended data
        images_extended_data = data.pop('imagesExtended', None)
        if images_extended_data:
            master_url = images_extended_data[0]['highResolution']['original'][0]['url']
            master_format = images_extended_data[0]['highResolution']['original'][0]['format']
        else:
            print("Error: imagesExtended missing")
            exit(1)

        # Extract the Summary
        summary_data = data.pop('summary', '')
        if summary_data:
            summary = FinnaSummary(text=summary_data)
            summary.save()
        else:
            summary = None

        # Create the book instance
        record, created = self.get_or_create(finna_id=data['id'], defaults={'image_right': image_rights})
        record.title = data['title']
        record.short_title = data['shortTitle']
        record.identifier_string = data.pop('identifierString', None)
        record.year = data.pop('year', None)
        record.number_of_images = len(images_data)
        record.master_url = master_url
        record.master_format = master_format
        record.measurements = data['measurements']

        try:
            record.date_string = data['events']['valmistus'][0]['date']
        except:
            print("Skipping date_string")

        if summary:
            record.summary = summary

        for non_presenter_author in non_presenter_authors:
            record.non_presenter_authors.add(non_presenter_author)

        for building in buildings:
            record.buildings.add(building)

        for subject in subjects:
            record.subjects.add(subject)

        for subject_place in subject_places:
            record.subject_places.add(subject_place)

        for subject_actor in subject_actors:
            record.subject_actors.add(subject_actor)

        for subject_detail in subject_details:
            record.subject_details.add(subject_detail)

        for collection in collections:
            record.collections.add(collection)

        for institution in institutions:
            record.institutions.add(institution)

        record.image_right = image_rights
        record.save()

        return record


class FinnaImage(models.Model):
    finna_id = models.CharField(max_length=200, null=False, blank=False, db_index=True, unique=True)
    title = models.CharField(max_length=200)
    year = models.PositiveIntegerField(unique=False, null=True, blank=True)
    date_string = models.CharField(max_length=200, null=True, blank=True)
    number_of_images = models.PositiveIntegerField(unique=False, null=True, blank=True)
    master_url = models.URLField(max_length=500)
    master_format = models.CharField(max_length=16)
    measurements = models.CharField(max_length=32)
    non_presenter_authors = models.ManyToManyField(FinnaNonPresenterAuthor)
    summary = models.ForeignKey(FinnaSummary, related_name='summary', blank=True, null=True, on_delete=models.CASCADE)
    subjects = models.ManyToManyField(FinnaSubject)
    subject_places = models.ManyToManyField(FinnaSubjectPlace)
    subject_actors = models.ManyToManyField(FinnaSubjectActor)
    subject_details = models.ManyToManyField(FinnaSubjectDetail)
    collections = models.ManyToManyField(FinnaCollection)
    buildings = models.ManyToManyField(FinnaBuilding)
    institutions = models.ManyToManyField(FinnaInstitution)
    image_right = models.ForeignKey(FinnaImageRight, on_delete=models.RESTRICT)

    # Accession number or similar identifier
    identifier_string = models.CharField(max_length=64, null=True, blank=True)
    short_title = models.CharField(max_length=200, null=True, blank=True)

    # Pseudo properties
    @property
    def thumbnail_url(self):
        url = f'https://finna.fi/Cover/Show?source=Solr&id={self.finna_id}&index=0&size=small'
        return url

    @property
    def image_url(self):
        url = f'https://finna.fi/Cover/Show?source=Solr&id={self.finna_id}&index=0&size=large'
        return url

    @property
    def url(self):
        url = f'https://finna.fi/Record/{self.finna_id}'
        return url

    @property
    def finna_json(self):
        url = get_finna_record_url(self.finna_id, True)
        return url

    @property
    def pseudo_filename(self):
        if self.master_format == 'tif':
            name = self.short_title
            name = name.replace(" ", "_")
            name = name.replace(":", "_")
            identifier = self.identifier_string.replace(":", "-")
            file_name = f'{name}_({identifier}).tif'
            return file_name

        else:
            print(f'Unknown format: {self.master_format}')
            exit(1)

    objects = FinnaRecordManager()


class FinnaImageHash(models.Model):
    phash = models.BigIntegerField(null=True)  # To store 64-bit unsigned integer
    dhash = models.BigIntegerField(null=True)  # To store 64-bit unsigned integer
    dhash_vertical = models.BigIntegerField(null=True)  # To store 64-bit unsigned integer
    finna_image = models.ForeignKey(FinnaImage, related_name="image_hashes", on_delete=models.CASCADE)

    class Meta:
        unique_together = [['phash', 'finna_image'], ['dhash', 'finna_image'], ['dhash_vertical', 'finna_image']]


class FinnaImageHashURL(models.Model):
    url = models.URLField(max_length=500)
    imagehash = models.ForeignKey(FinnaImageHash, related_name="image_urls", on_delete=models.CASCADE)
    width = models.PositiveIntegerField(null=False, default=0)
    height = models.PositiveIntegerField(null=False, default=0)
    index = models.PositiveIntegerField(null=False, default=0)
    thumbnail = models.BooleanField(default=False)
    created = models.DateTimeField(default=timezone.now)


class ToolforgeImageHashCache(models.Model):
    page_id = models.PositiveIntegerField()
    phash = models.BigIntegerField(null=True, db_index=True)  # To store 64-bit unsigned integer
    dhash = models.BigIntegerField(null=True, db_index=True)  # To store 64-bit unsigned integer


# Updates the Image.confirmed_finna_id_updated_at when confirmed_finna_id is updated
@receiver(pre_save, sender=Image)
def update_timestamp(sender, instance, **kwargs):
    # If the instance exists, means it's not a new record
    if instance.pk:
        old_instance = Image.objects.get(pk=instance.pk)
        if old_instance.finna_id_confirmed != instance.finna_id_confirmed:
            instance.finna_id_confirmed_at = timezone.now()
