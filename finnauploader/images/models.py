from watson import search as watson
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.db.utils import DataError
import re
import json
import urllib
from datetime import datetime
# from images.locations import parse_subject_place_string
from images.finna_record_api import get_finna_record_url, parse_full_record
from images.pywikibot_helpers import get_wikidata_id_from_url
from images.wikitext.timestamps import parse_timestamp
from images.duplicatedetection import is_already_in_commons
# import images.models_mappingcache
from images.wikitext.wikidata_helpers import get_author_wikidata_id, \
                                    get_subject_actors_wikidata_id, \
                                    get_institution_wikidata_id, \
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
    value = models.CharField(max_length=128)
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
    value = models.CharField(max_length=128)
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
    page_title = models.CharField(max_length=250)
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


# description of physical structure where collection/item/object may be placed in
class FinnaBuilding(models.Model):
    value = models.CharField(max_length=128)
    translated = models.CharField(max_length=128)

    def __str__(self):
        return self.translated


# description of copyright, permissions, licensing information
class FinnaImageRight(models.Model):
    copyright = models.CharField(max_length=64)
    link = models.URLField(max_length=500)
    description = models.TextField()

    def __str__(self):
        return self.copyright

    def get_link(self):
        return self.link

    def get_copyright(self):
        return self.copyright

    def get_description(self):
        return self.description


# non-presenter may be creator of is_photograph
# or creator of object in image
class FinnaNonPresenterAuthor(models.Model):
    name = models.CharField(max_length=128)
    role = models.CharField(max_length=128)
    wikidata_id = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self):
        return self.name

    def get_wikidata_id(self):
        return get_author_wikidata_id(self.name)

    def is_photographer(self):
        # note: SLS uses "pht"
        known_roles = ['kuvaaja', 'valokuvaaja', 'Valokuvaaja', 'pht']
        if (self.role in known_roles):
            return True
        return False

    def is_architect(self):
        if (self.role == 'arkkitehti' or self.role == 'Arkkitehti'):
            return True
        return False


# another title for the item
class FinnaAlternativeTitle(models.Model):
    text = models.TextField()
    lang = models.CharField(max_length=6)
    pref = models.CharField(max_length=16)

    def __str__(self):
        return self.text


# description of the item
class FinnaSummary(models.Model):
    text = models.TextField()
    lang = models.CharField(max_length=6)
    order = models.PositiveIntegerField(unique=False)

    def __str__(self):
        return self.text


class FinnaSubject(models.Model):
    name = models.TextField()

    def __str__(self):
        return self.name


class FinnaSubjectWikidataPlace(models.Model):
    uri = models.URLField(max_length=500)

    def __str__(self):
        return self.uri


class FinnaSubjectExtented(models.Model):
    heading = models.TextField()
    type = models.CharField(max_length=50)
    record_id = models.CharField(max_length=255, null=True, blank=True)
    ids = models.JSONField(null=True, blank=True)
    detail = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.heading


class FinnaSubjectPlace(models.Model):
    name = models.TextField()
    wikidata_id = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self):
        return self.name


class FinnaSubjectActor(models.Model):
    name = models.TextField()
    wikidata_id = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self):
        return self.name

    def get_wikidata_id(self):
        wikidata_id = get_subject_actors_wikidata_id(self.name)
        return wikidata_id


class FinnaSubjectDetail(models.Model):
    name = models.TextField()

    def __str__(self):
        return self.name


class FinnaCollection(models.Model):
    name = models.TextField()

    def __str__(self):
        return self.name

    def get_wikidata_id(self):
        wikidata_id = get_collection_wikidata_id(self.name)
        return wikidata_id


class FinnaInstitution(models.Model):
    value = models.TextField()
    translated = models.TextField()

    def __str__(self):
        return self.value

    def get_wikidata_id(self):
        wikidata_id = get_institution_wikidata_id(self.translated)
        return wikidata_id


# Dynamic subjects based on wiki categories / wikidata items
class FinnaLocalSubject(models.Model):
    value = models.TextField()
    normalized_name = models.CharField(max_length=200)

    def __str__(self):
        return self.value

    def get_wikidata_id(self):
        return get_wikidata_id_from_url(self.value)


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
        subject_places = [FinnaSubjectPlace.objects.get_or_create(name=subject_place_name.strip())[0] for subject_place_name in subject_places_data]

        # Extract and handle subjectExtented data
        subject_extented_data = data.pop('subjectsExtended', [])
        subject_extented = []
        for se in subject_extented_data:
            heading = se['heading'][0].strip()
            if 'type' not in se:
                # skip if not included?
                #continue
                se['type'] = ''
            
            if 'id' not in se:
                se['id'] = ''

            if 'ids' not in se:
                se['ids'] = []

            if 'detail' not in se:
                se['detail'] = ''

            r, created = FinnaSubjectExtented.objects.get_or_create(heading=heading, type=se['type'], record_id=se['id'], ids=se['ids'], detail=se['detail'])
            subject_extented.append(r)

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
        try:
            image_rights_copyright = image_rights_data['copyright']
        except:
            print("ERROR saving copyright ----")
            print(json.dumps(data))
            print("ERROR ----")
            exit(1)
        image_rights_link = image_rights_data['link']
        image_rights_description = image_rights_data.get('description', '')
        # TODO : if description has link to creative commons, replace http:// by https://
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
            if (master_url.startswith("/Cover/Show") is True):
                master_url = "https://finna.fi" + master_url
            else:
                # might be another museovirasto link, but in different domain
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

            # note: if there is no language specified, we should have a placeholder?
            # currently following handling does not support it
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
            if 'attributes' not in s:
                continue
            if 'label' not in s['attributes']:
                continue
            if 'lang' not in s['attributes']:
                continue
            # data from certain collections does not have "pref" in the full record
            if 'pref' not in s['attributes']:
                continue

            # tag appellationValue ?
            alt_title, created = obj.get_or_create(text=s['text'],
                                                   lang=s['attributes']['lang'],
                                                   pref=s['attributes']['pref'])

            # TODO: parse classification><term lang="fi" label="luokitus"
            # has information like >mustavalkoinen  negatiivi< that we can further categorize with later

            alternative_titles.append(alt_title)

        # classification
        
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
        #record.physical_descriptions = "\n".join(data['physicalDescriptions'])

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

        for se in subject_extented:
            record.subject_extented.add(se)

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
        except DataError as e:
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
    master_format = models.TextField()
    measurements = models.TextField()
    #physical_descriptions = models.TextField() # mostly empty anyway
    non_presenter_authors = models.ManyToManyField(FinnaNonPresenterAuthor)
    summaries = models.ManyToManyField(FinnaSummary)
    subjects = models.ManyToManyField(FinnaSubject)
    subject_extented = models.ManyToManyField(FinnaSubjectExtented)
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
    # note that this can be array of short identifiers in some collections
    identifier_string = models.CharField(max_length=128, null=True, blank=True)
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
    def filename_extension(self):
        format_to_extension = {
            'tif': 'tif',
            'tiff': 'tif',
            'image/tiff': 'tif',
            'png': 'png',
            'image/png': 'png',
            'jpg': 'jpg',
            'jpeg': 'jpg',
            'image/jpeg': 'jpg',
            'gif': 'gif',
            'image/gif': 'gif'
        }

        try:
            extension = format_to_extension[self.master_format]
            return extension
        except:
            print(f'Unknown format: {self.master_format}')
            exit(1)

    @property
    def pseudo_filename(self):
        filename_extension = self.filename_extension
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
            if (self.short_title is not None and len(self.short_title) < 250):
                print("using short title name")
                name = self.short_title
            elif (alt_title_name is not None and len(str(alt_title_name)) < 250):
                print("using alt title name")
                name = alt_title_name.text
            elif (summaries_name is not None and len(str(summaries_name)) < 250):
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
        if (self.date_string is not None):
            timestamp, precision = parse_timestamp(self.date_string)
            if (timestamp is not None):
                if (year != str(timestamp.year)):
                    print("year " + year + " does not match date string " + str(timestamp.year) + ", ignoring it")
                    year = ''

        # some images don't have identifier to be used
        if (self.identifier_string is not None):
            identifier = self.identifier_string.replace(":", "-")
            identifier = identifier.replace("/", "_")
        else:
            identifier = ''

        name = name.replace(" ", "_")
        name = name.replace("/", "_")   # don't allow slash in names
        name = name.replace("\n", " ")  # don't allow newline in names
        name = name.replace("\t", " ")  # don't allow tabulator in names
        name = name.replace("\r", " ")  # don't allow carriage return in names

        # try to remove soft-hyphens from name while we can
        # note: 0xC2 0xAD in utf-8, 0x00AD in utf-16, which one is used?
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

        if (len(year) > 0):
            year = year + '_'
        if (len(identifier) > 0):
            file_name = f'{name}_{year}({identifier}).{filename_extension}'
        else:
            # in some odd cases there is no identifier (accession number) for the file
            file_name = f'{name}_{year}.{filename_extension}'

        # replace non-breakable spaces with normal spaces
        # 0xC2 0xA0 in utf-8, 0x00A0 in utf-16
        file_name = file_name.replace(u"\u00A0", " ")

        # wiki doesn't allow non-breakable spaces
        quoted_name = urllib.parse.quote_plus(file_name)
        quoted_name = quoted_name.replace("%C2%A0", " ")
        file_name = urllib.parse.unquote(quoted_name)

        return file_name

    def __str__(self):
        return self.finna_id

    # this is still in class FinnaImage, many others have member "finna_id" as well..
    def get_finna_id(self):
        return self.finna_id

    def get_date_string(self):
        return self.date_string

    def is_entry_in_subjects(self, name):
        for subject in self.subjects.all():
            if name == subject.name:
                return True
        return False


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
