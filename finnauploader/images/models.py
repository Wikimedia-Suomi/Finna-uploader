from watson import search as watson
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
import re
import urllib
from datetime import datetime
# from images.locations import parse_subject_place_string
from images.finna import get_finna_record_url, parse_full_record
from images.pywikibot_helpers import get_wikidata_id_from_url
from images.wikitext.timestamps import parse_timestamp
from images.sdc_helpers import create_P571_inception
from images.duplicatedetection import is_already_in_commons
from images.sdc_helpers import create_P275_licence, \
                                           create_P6216_copyright_state, \
                                           create_P9478_finna_id, \
                                           create_P195_collection, \
                                           create_P180_depict, \
                                           create_P7482_source_of_file, \
                                           create_P170_author

from images.wikitext.cache_wikidata import get_author_wikidata_id, \
                                    get_creator_template_from_wikidata_id, \
                                    get_subject_actors_wikidata_id, \
                                    get_subject_image_category_from_wikidata_id, \
                                    get_creator_image_category_from_wikidata_id, \
                                    get_institution_wikidata_id, \
                                    get_institution_template_from_wikidata_id, \
                                    get_collection_wikidata_id


def update_dates_in_filename(input_str):
    # Regular expression to find the date in the format d.m.yyyy
    date_pattern = r"\d{1,2}\.\d{1,2}\.\d{4}"
    found_date = re.search(date_pattern, input_str)

    if found_date:
        # Extract the date
        date_str = found_date.group()

        # Parse the date
        date_obj = datetime.strptime(date_str, "%d.%m.%Y")

        # Format the date into the desired format
        formatted_date = date_obj.strftime("%Y-%m-%d")

        # Replace the old date in the string with the new formatted date
        output_str = input_str.replace(date_str, formatted_date)
    else:
        output_str = input_str
    return output_str


# Create your models here.

class FintoYsoLabel(models.Model):
    value = models.CharField(max_length=64)
    lang = models.CharField(max_length=8)


class FintoYsoMMLPlaceType(models.Model):
    uri = models.URLField(max_length=500)


class FintoYsoWikidataPlaceType(models.Model):
    uri = models.URLField(max_length=500)


class FintoYsoCloseMatch(models.Model):
    uri = models.URLField(max_length=500)


class FintoYsoPlace(models.Model):
    yso_id = models.CharField(max_length=8)
    labels = models.ManyToManyField(FintoYsoLabel, related_name='places')
    close_matches = models.ManyToManyField(FintoYsoCloseMatch)
    wikidata_place_types = models.ManyToManyField(FintoYsoWikidataPlaceType)
    mml_place_types = models.ManyToManyField(FintoYsoMMLPlaceType)
    lat = models.DecimalField(max_digits=22, decimal_places=16, blank=True, null=True)
    long = models.DecimalField(max_digits=22, decimal_places=16, blank=True, null=True)


class LocationTestCache(models.Model):
    location = models.URLField(max_length=500)
    entity = models.URLField(max_length=500)
    value = models.BooleanField()


class CacheSparqlBool(models.Model):
    query_id = models.CharField(max_length=64)
    value = models.BooleanField()


class FintoYsoMissingCache(models.Model):
    value = models.CharField(max_length=64)
    finna_id = models.CharField(max_length=200, null=False, blank=False)


# Commons image
class Image(models.Model):
    page_id = models.PositiveIntegerField(unique=True)
    page_title = models.CharField(max_length=250)
    finna_id = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    finna_id_confirmed = models.BooleanField(default=False)
    finna_id_confirmed_at = models.DateTimeField(null=True, blank=True)


class WikimediaCommonsImage(models.Model):
    page_id = models.PositiveIntegerField(unique=True)
    page_title = models.CharField(max_length=200)
    match_type = models.CharField(max_length=16, db_index=True)


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

    def get_copyright_template(self):
        if self.copyright == "CC BY 4.0":
            return "{{CC-BY-4.0}}\n{{FinnaReview}}"
        elif self.copyright == "CC BY-SA 4.0":
            return "{{CC BY-SA 4.0}}\n{{FinnaReview}}"
        else:
            print("Unknown copyright: " + self.copyright)
            exit(1)

    def get_permission_string(self):
        if self.link:
            ret = f'[{self.link} {self.copyright}]; {self.description}'
        else:
            ret = f'{self.copyright}; {self.description}'
        return ret

    def get_licence_claim(self):
        return create_P275_licence(value=self.copyright)

    def get_copyright_state_claim(self):
        return create_P6216_copyright_state(value=self.copyright)


class FinnaNonPresenterAuthor(models.Model):
    name = models.CharField(max_length=64)
    role = models.CharField(max_length=64)
    wikidata_id = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self):
        return self.name

    def get_wikidata_id(self):
        return get_author_wikidata_id(self.name)

    def get_creator_template(self):
        wikidata_id = self.get_wikidata_id()
        return get_creator_template_from_wikidata_id(wikidata_id)

    def get_creator_category(self, prefix=None):
        wikidata_id = self.get_wikidata_id()
        category = get_subject_image_category_from_wikidata_id(wikidata_id, True)
        if not prefix:
            category = category.replace('Category:', '')
        return category

    def get_photos_category(self, prefix=None):
        wikidata_id = self.get_wikidata_id()
        category = get_creator_image_category_from_wikidata_id(wikidata_id)
        if not prefix:
            category = category.replace('Category:', '')
        return category

    def get_photographer_author_claim(self):
        if self.role != 'kuvaaja' and self.role != 'valokuvaaja':
            print(f'{self} is not photographer')
            exit(1)

        wikidata_id = self.get_wikidata_id()
        role = 'Q33231'  # valokuvaaja
        claim = create_P170_author(wikidata_id, role)
        return claim


class FinnaAlternativeTitle(models.Model):
    text = models.TextField()
    lang = models.CharField(max_length=6)
    pref = models.CharField(max_length=16)

    def __str__(self):
        return self.text


class FinnaSummary(models.Model):
    text = models.TextField()
    lang = models.CharField(max_length=6)
    order = models.PositiveIntegerField(unique=False)

    def __str__(self):
        return self.text


class FinnaSubject(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class FinnaSubjectWikidataPlace(models.Model):
    uri = models.URLField(max_length=500)

    def __str__(self):
        return self.uri


class FinnaSubjectPlace(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class FinnaSubjectActor(models.Model):
    name = models.CharField(max_length=200)
    wikidata_id = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self):
        return self.name

    def get_wikidata_id(self):
        wikidata_id = get_subject_actors_wikidata_id(self.name)
        return wikidata_id

    def get_commons_category(self, prefix=None):
        wikidata_id = self.get_wikidata_id()
        category = get_subject_image_category_from_wikidata_id(wikidata_id, True)
        if not prefix:
            category = category.replace('Category:', '')
        return category

    def get_depict_claim(self):
        wikidata_id = self.get_wikidata_id()
        return create_P180_depict(wikidata_id)


class FinnaSubjectDetail(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class FinnaCollection(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name

    def get_wikidata_id(self):
        wikidata_id = get_collection_wikidata_id(self.name)
        return wikidata_id

    def get_collection_claim(self, identifier=None):
        wikidata_id = self.get_wikidata_id()
        return create_P195_collection(wikidata_id, identifier)


class FinnaInstitution(models.Model):
    value = models.CharField(max_length=200)
    translated = models.CharField(max_length=200)

    def __str__(self):
        return self.value

    def get_wikidata_id(self):
        wikidata_id = get_institution_wikidata_id(self.translated)
        return wikidata_id

    def get_institution_template(self):
        wikidata_id = self.get_wikidata_id()
        return get_institution_template_from_wikidata_id(wikidata_id)


# Dynamic subjects based on wiki categories / wikidata items
class FinnaLocalSubject(models.Model):
    value = models.CharField(max_length=400)
    normalized_name = models.CharField(max_length=200)

    def __str__(self):
        return self.value

    def get_wikidata_id(self):
        return get_wikidata_id_from_url(self.value)

    def get_category_name(self, prefix=None):
        self.value = self.value.replace('category:', 'Category:')

        if 'https://commons.wikimedia.org/wiki/Category:' in self.value:
            return self.value.replace('https://commons.wikimedia.org/wiki/Category:', '')

        if 'http://commons.wikimedia.org/wiki/category:' in self.value:
            return self.value.replace('http://commons.wikimedia.org/wiki/Category:', '')

        if '^Category:' in self.value:
            return self.value.replace('Category:', '')

        wikidata_id = self.get_wikidata_id()
        if wikidata_id:
            category = get_subject_image_category_from_wikidata_id(wikidata_id)
            if category:
                if not prefix:
                    category = category.replace('Category:', '')
                return category
        return None

    def get_depict_claim(self):
        wikidata_id = self.get_wikidata_id()
        return create_P180_depict(wikidata_id)


# Managers
class FinnaRecordManager(models.Manager):

    def update_wikidata_ids(self):
        authors = FinnaNonPresenterAuthor.objects.all()
        for author in authors:
            try:
                wikidata_id = author.get_wikidata_id()
                if author.wikidata_id != wikidata_id:
                    author.wikidata_id = wikidata_id
                    author.save(update_fields=['wikidata_id'])
            except:
                pass

        actors = FinnaSubjectActor.objects.all()
        for actor in actors:
            try:
                wikidata_id = actor.get_wikidata_id()
                if actor.wikidata_id != wikidata_id:
                    actor.wikidata_id = wikidata_id
                    actor.save(update_fields=['wikidata_id'])
            except:
                pass

        images = FinnaImage.objects.filter(already_in_commons=False)
        for image in images:
            uploaded = is_already_in_commons(image.finna_id, fast=True)
            if uploaded:
                image.already_in_commons = uploaded
                image.save(update_fields=['already_in_commons'])

    # First try
    def create_from_data(self, data, local_data={}):

        def clean_subject_name(subject):
            if isinstance(subject, list):
                if len(subject) == 1:
                    subject = subject[0]
                else:
                    print("Error: Unexpected subject format")
                    print(subject)
                    exit(1)
            return subject

        # Extract and handle non_presenter_authors data
        non_presenter_authors_data = data.pop('nonPresenterAuthors', [])
        non_presenter_authors = []
        for non_presenter_author_data in non_presenter_authors_data:
            author = FinnaNonPresenterAuthor.objects.get_or_create(
                name=non_presenter_author_data['name'],
                role=non_presenter_author_data['role']
                )[0]
            try:
                # Update wikidata id
                wikidata_id = author.get_wikidata_id()
                if author.wikidata_id != wikidata_id:
                    author.wikidata_id = wikidata_id
                    author.save(update_fields=['wikidata_id'])
            except:
                pass

            non_presenter_authors.append(author)

        # Extract and handle buildings data
        buildings_data = data.pop('buildings', [])
        buildings = [FinnaBuilding.objects.get_or_create(value=building_data['value'], defaults={'translated': building_data['translated']})[0] for building_data in buildings_data]

        # Extract and handle subjects data
        subjects_data = data.pop('subjects', [])
        subjects = [FinnaSubject.objects.get_or_create(name=clean_subject_name(subject_name))[0] for subject_name in subjects_data]

        # Extract and handle subjectPlaces data
        subject_places_data = data.pop('subjectPlaces', [])
        subject_places = [FinnaSubjectPlace.objects.get_or_create(name=subject_place_name)[0] for subject_place_name in subject_places_data]

        # Extract and handle subjectActors data
        subject_actors_data = data.pop('subjectActors', [])
        subject_actors = [FinnaSubjectActor.objects.get_or_create(name=subject_actor_name)[0] for subject_actor_name in subject_actors_data]
        for subject_actor in subject_actors:
            try:
                # Update wikidata id
                wikidata_id = subject_actor.get_wikidata_id()
                if subject_actor.wikidata_id != wikidata_id:
                    subject_actor.wikidata_id = wikidata_id
                    subject_actor.save(update_fields=['wikidata_id'])
            except:
                pass

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
        image_rights_copyright = image_rights_data['copyright']
        image_rights_link = image_rights_data['link']
        image_rights_description = image_rights_data.get('description', '')
        image_right, created = FinnaImageRight.objects.get_or_create(copyright=image_rights_copyright,
                                                                     link=image_rights_link,
                                                                     description=image_rights_description)

        # Extract images data
        images_data = data.pop('images', [])

        # Extract imagesExtended data
        images_extended_data = data.pop('imagesExtended', None)
        if images_extended_data:
            try:
                master_url = images_extended_data[0]['highResolution']['original'][0]['url']
                master_format = images_extended_data[0]['highResolution']['original'][0]['format']
            except:
                # If no highResolution or original image
                master_url = images_extended_data[0]['urls']['large']
                master_format = 'image/jpeg'
        else:
            print("Error: imagesExtended missing")
            exit(1)

        # in some cases, url is not complete:
        # protocol and domain are not stored in the record, which we need later
        if (master_url.find("http://") < 0 and master_url.find("https://") < 0):
            if (master_url.startswith("/Cover/Show") == True):
                master_url = "https://finna.fi" + master_url
            else:
                print("Warn: not a Finna url and not complete url? ", master_url)

        # Extract the Summary
        # Data which is stored to separate tables
        full_record_data = parse_full_record(data['fullRecord'])

        summaries = []
        obj = FinnaSummary.objects
        for s in full_record_data['summary']:
            if 'text' not in s:
                continue
            if not s['text']:
                continue

            if 'JOKA' not in str(collections_data):
                continue

            if 'lang' not in s['attributes']:
                continue

            try:
                summary, created = obj.get_or_create(
                                                 text=s['text'],
                                                 lang=s['attributes']['lang'],
                                                 defaults={'order': 1})
            except:
                print(s)
                exit(1)
            summaries.append(summary)

        alternative_titles = []
        obj = FinnaAlternativeTitle.objects
        for s in full_record_data['title']:
            if 'text' not in s:
                continue
            if not s['text']:
                continue
            if 'label' not in s['attributes']:
                continue

            alt_title, created = obj.get_or_create(text=s['text'],
                                                   lang=s['attributes']['lang'],
                                                   pref=s['attributes']['pref'])
            alternative_titles.append(alt_title)

        # Extract local add_categories data
        add_categories_data = local_data.pop('add_categories', [])
        add_categories = [FinnaLocalSubject.objects.get_or_create(value=value)[0] for value in add_categories_data]

        add_depicts_data = local_data.pop('add_depicts', [])
        add_depicts = [FinnaLocalSubject.objects.get_or_create(value=value)[0] for value in add_depicts_data]

        # Create the book instance
        record, created = self.get_or_create(finna_id=data['id'], defaults={'image_right': image_right})
        record.title = data.get('title', '')
        record.short_title = data.get('shortTitle', '')
        record.identifier_string = data.pop('identifierString', None)
        record.year = data.pop('year', None)
        record.number_of_images = len(images_data)
        record.master_url = master_url
        record.master_format = master_format
        record.measurements = "\n".join(data['measurements'])

        try:
            record.date_string = data['events']['valmistus'][0]['date']
        except:
            print(record.finna_json_url)
            print('Skipping date_string')
#            exit(1)

        record.summaries.clear()
        for summary in summaries:
            record.summaries.add(summary)

        record.alternative_titles.clear()
        for alternative_title in alternative_titles:
            record.alternative_titles.add(alternative_title)

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

        record.add_categories.clear()
        for add_category in add_categories:
            record.add_categories.add(add_category)

        record.add_depicts.clear()
        for add_depict in add_depicts:
            record.add_depicts.add(add_depict)

        record.image_right = image_right

        search_index, created = FinnaRecordSearchIndex.objects.get_or_create(datatext=str(data))
        record.data = search_index

        try:
            record.save()
        except django.db.utils.DataError as e:
            print('Error: {}'.format(e))
            exit(1)

        return record


class FinnaRecordSearchIndex(models.Model):
    datatext = models.TextField()


class FinnaImage(models.Model):
    objects = FinnaRecordManager()

    finna_id = models.CharField(max_length=200, null=False, blank=False, db_index=True, unique=True)
    title = models.TextField()
    alternative_titles = models.ManyToManyField(FinnaAlternativeTitle)
    year = models.PositiveIntegerField(unique=False, null=True, blank=True)
    date_string = models.TextField()
    number_of_images = models.PositiveIntegerField(unique=False, null=True, blank=True)
    master_url = models.URLField(max_length=500)
    master_format = models.CharField(max_length=200)
    measurements = models.CharField(max_length=200)
    non_presenter_authors = models.ManyToManyField(FinnaNonPresenterAuthor)
    summaries = models.ManyToManyField(FinnaSummary)
    subjects = models.ManyToManyField(FinnaSubject)
    subject_places = models.ManyToManyField(FinnaSubjectPlace)
    subject_actors = models.ManyToManyField(FinnaSubjectActor)
    subject_details = models.ManyToManyField(FinnaSubjectDetail)
    collections = models.ManyToManyField(FinnaCollection)
    buildings = models.ManyToManyField(FinnaBuilding)
    institutions = models.ManyToManyField(FinnaInstitution)
    image_right = models.ForeignKey(FinnaImageRight, on_delete=models.RESTRICT)
    add_categories = models.ManyToManyField(FinnaLocalSubject, related_name="category_images")
    add_depicts = models.ManyToManyField(FinnaLocalSubject, related_name="depict_images")
    best_wikidata_location = models.ManyToManyField(FinnaSubjectWikidataPlace)
    commons_images = models.ManyToManyField(WikimediaCommonsImage)
    already_in_commons = models.BooleanField(default=False)
    skipped = models.BooleanField(default=False)
    data = models.ForeignKey(FinnaRecordSearchIndex, on_delete=models.RESTRICT, null=True, blank=True)

    # Accession number or similar identifier
    identifier_string = models.CharField(max_length=64, null=True, blank=True)
    short_title = models.TextField()

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
    def finna_json_url(self):
        url = get_finna_record_url(self.finna_id, True)
        return url

    @property
    def pseudo_filename(self):
        format_to_extension = {
            'tif': 'tif',
            'tiff': 'tif',
            'png': 'png',
            'jpg': 'jpg',
            'jpeg': 'jpg',
            'image/jpeg': 'jpg'
        }

        extension = ""
        if self.master_format in format_to_extension:
            extension = format_to_extension[self.master_format]
        
        if (len(extension) == 0):
            print(f'Unknown format: {self.master_format}')
            exit(1)
            
        summaries_name = self.summaries.filter(lang='en').first()
        alt_title_name = self.alternative_titles.filter(lang='en').first()

        name = None
        if summaries_name and alt_title_name:
            if len(str(summaries_name)) > len(str(alt_title_name)):
                name = alt_title_name.text
            else:
                name = summaries_name.text

        if not name:
            name = self.short_title
            
        # filename in commons can't exceed 250 bytes:
        # let's assume we have narrow ASCII only..
        if (len(name) > 250):
            if (self.short_title != None and len(self.short_title) < 250):
                print("using short title name")
                name = self.short_title
            elif (alt_title_name != None and len(str(alt_title_name)) < 250):
                print("using alt title name")
                name = alt_title_name.text
            elif (summaries_name != None and len(str(summaries_name)) < 250):
                print("using summaries name")
                name = summaries_name.text
            else:
                print("unable to find name shorter than maximum for filename")
            
        name = update_dates_in_filename(name)
        name = name.replace('content description: ', '')
        name = name.replace(".", "_")
        name = name.replace(" ", "_")
        name = name.replace(":", "_")
        name = name.replace("_", " ").strip()
        
        if self.year and str(self.year) not in name:
            year = f'{self.year}'
        else:
            year = ''

        # if there is large difference in year don't add it to name:
        # year in different fields can vary a lot
        if (self.date_string != None):
            timestamp, precision = parse_timestamp(self.date_string)
            if (timestamp != None):
                if (year != str(timestamp.year)):
                    print("year " + year + " does not match date string " + str(timestamp.year) + ", ignoring it")
                    year = ''
        if (len(year) > 0):
            year = year + '_'

        # some images don't have identifier to be used
        if (self.identifier_string != None):
            identifier = self.identifier_string.replace(":", "-")
            identifier = identifier.replace("/", "_")
        else:
            identifier = ''

        name = name.replace(" ", "_")
        name = name.replace("/", "_") # don't allow slash in names
        name = name.replace("\n", " ") # don't allow newline in names
        name = name.replace("\t", " ") # don't allow tabulator in names
        name = name.replace("\r", " ") # don't allow carriage return in names

        # try to remove soft-hyphens from name while we can
        name = name.replace(u"\u00A0", "")
        name = name.replace("\xc2\xa0", "")

        if ((len(name) + len(year) + len(identifier)) > 240):
            print("filename is becoming too long, limiting it")
            
        # each character with umlaut becomes at least three in HTML-encoding..
        quoted_name = urllib.parse.quote_plus(name)
        if (len(quoted_name) > 200):
            print("filename is becoming too long, limiting it")
            name = name[:200] + "__"
            print("new name: ", name)
            
        # wiki doesn't allow soft hyphen in names:
        # normal replace() does not work on silent characters for some reason?
        # -> kludge around it
        quoted_name = urllib.parse.quote_plus(name)
        quoted_name = quoted_name.replace("%C2%AD", "") 
        name = urllib.parse.unquote(quoted_name)

        if (len(identifier) > 0):
            file_name = f'{name}_{year}({identifier}).{extension}'
        else:
            # in some odd cases there is no identifier (accession number) for the file
            file_name = f'{name}_{year}.{extension}'

        return file_name

    def __str__(self):
        return self.finna_id

    def get_creator_templates(self):
        creator_templates = []
        # TODO: role may be also "valokuvaaja" -> what to do here?
        for creator in self.non_presenter_authors.filter(role='kuvaaja'):
            template = creator.get_creator_template()
            creator_templates.append(template)
        return "".join(creator_templates)

    def get_institution_templates(self):
        institution_templates = []
        for institution in self.institutions.all():
            template = institution.get_institution_template()
            institution_templates.append(template)
        return "".join(institution_templates)

    def get_permission_string(self):
        return self.image_right.get_permission_string()

    def get_copyright_template(self):
        return self.image_right.get_copyright_template()

    def get_sdc_labels(self):
        
        labels = {}
        labels['fi'] = {'language': 'fi', 'value': self.title}

        for title in self.alternative_titles.all():
            labels[title.lang] = {'language': title.lang, 'value': title.text}

        # TODO if label exceeds max length use title or short title instead,
        # use long description only if known to fit in 250 character limit
        #for summary in self.summaries.all():
            #text = str(summary.text)
            #text = text.replace('sisällön kuvaus: ', '')
            #text = text.replace('innehållsbeskrivning: ', '')
            #text = text.replace('content description: ', '')

            #labels[summary.lang] = {'language': summary.lang, 'value': text}

        return labels

    def get_finna_id_claim(self):
        return create_P9478_finna_id(self.finna_id)

    def get_inception_claim(self):
        try:
            timestamp, precision = parse_timestamp(self.date_string)

            if timestamp and precision:
                claim = create_P571_inception(timestamp, precision)
                return claim
        except:
            return None

    def get_source_of_file_claim(self):
        # TODO: when using beyond JOKA-archive, fetch correct values per image
        publisher = 'Q3029524'  # Finnish Heritage Agency
        operator = 'Q420747'    # National library
        url = self.url
        
        instlist = list()

        # FIXME: Only Finnish heritage agency images are supported now
        for institution in self.institutions.all():
            #instcode = get_institution_wikidata_id(institution.name)
            instlist.append(institution.get_wikidata_id())

            #if institution.get_wikidata_id() != publisher:
                #print(f'{institution} wikidata id is not {publisher}')
                #exit(1)
        if (len(instlist) == 0):
            print(f'no institutions found')
            exit(1)
        if (len(instlist) > 1):
            # TODO: check that create_P7482_source_of_file() can handle multiple institutions
            print(f'too many institutions found')
            exit(1)
                
        return create_P7482_source_of_file(url, operator, instlist[0])


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


watson.register(FinnaRecordSearchIndex)
