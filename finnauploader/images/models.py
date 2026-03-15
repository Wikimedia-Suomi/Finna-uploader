from watson import search as watson
from django.db import models
from django.db import transaction
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.db.utils import Error, DataError
import re
import json
import urllib
from datetime import datetime

import xml.etree.ElementTree as XEltree

# from images.locations import parse_subject_place_string
from images.wikitext.wikidata_helpers import get_author_wikidata_id, \
                                    get_subject_actors_wikidata_id, \
                                    get_institution_wikidata_id, \
                                    get_collection_wikidata_id, striprepeatespaces



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
    value = models.CharField(max_length=500)
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
    value = models.CharField(max_length=500)
    translated = models.CharField(max_length=500)

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
    name = models.CharField(max_length=200)
    role = models.CharField(max_length=128)
    wikidata_id = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self):
        return self.name

    #def get_wikidata_id(self):
    #    return wikidata_id

    def set_wikidata_id(self, wikidata_id):
        if (self.wikidata_id != wikidata_id):
            self.wikidata_id = wikidata_id
            self.save(update_fields=['wikidata_id'])

    def is_photographer(self):
        # note: SLS uses "pht"
        # also: "valokuvaamo" for studios
        known_roles = ['kuvaaja', 'valokuvaaja', 'Valokuvaaja', 'valokuvaamo', 'pht']
        if (self.role in known_roles):
            return True
        return False

    def is_architect(self):
        if (self.role == 'arkkitehti' or self.role == 'Arkkitehti'):
            return True
        return False
        # note: "kuvan kohteen tekijä" might be used for architect of a depicted building

    def is_illustrator(self):
        # kuvittaja? is it used?
        if (self.role == 'piirtäjä' or self.role == 'Piirtäjä'):
            return True
        return False

    # author: illustrator or other creator
    def is_creator(self):
        if (self.role == 'tekijä' or self.role == 'Tekijä'):
            return True
        return False
        # note: "alkuperäisen kuvan tekijä" in some drawings

    def is_publisher(self):
        if (self.role == 'kustantaja' or self.role == 'Kustantaja'):
            return True
        return False

    # "valmistaja" tai "valmistuttaja"
    def is_manufacturer(self):
        if (self.role == 'valmistaja' or self.role == 'Valmistaja'):
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
    type = models.CharField(max_length=250)
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
    
    # in some cases there is incorrect information in subject actors,
    # check if it should be skipped (no category, no wikidata-depiction, no category)
    def skip_actor(self):
        if (self.name == None or self.name == ""):
            return True
        skippable = ["null", "puoliso tohtori Thure Roos"]
        if self.name in skippable:
            return True
        return False

    #def get_wikidata_id(self):
    #    wikidata_id = wikidata_id
    #    return wikidata_id

    def set_wikidata_id(self, wikidata_id):
        if (self.wikidata_id != wikidata_id):
            self.wikidata_id = wikidata_id
            self.save(update_fields=['wikidata_id'])


class FinnaSubjectDetail(models.Model):
    name = models.TextField()

    def __str__(self):
        return self.name


class FinnaCollection(models.Model):
    name = models.TextField()
    wikidata_id = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self):
        return self.name

    #def get_wikidata_id(self):
    #    wikidata_id = wikidata_id
    #    return wikidata_id

    def set_wikidata_id(self, wikidata_id):
        if (self.wikidata_id != wikidata_id):
            self.wikidata_id = wikidata_id
            self.save(update_fields=['wikidata_id'])


class FinnaInstitution(models.Model):
    value = models.TextField()
    translated = models.TextField()
    wikidata_id = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self):
        return self.value

    def set_wikidata_id(self, wikidata_id):
        if (self.wikidata_id != wikidata_id):
            self.wikidata_id = wikidata_id
            self.save(update_fields=['wikidata_id'])


# Dynamic subjects based on wiki categories / wikidata items
class FinnaLocalSubject(models.Model):
    value = models.TextField()
    normalized_name = models.CharField(max_length=250)

    def __str__(self):
        return self.value

    def set_wikidata_id(self, wikidata_id):
        if (self.wikidata_id != wikidata_id):
            self.wikidata_id = wikidata_id
            self.save(update_fields=['wikidata_id'])

class FinnaClassifications(models.Model):
    value = models.TextField()
    lang = models.CharField(max_length=6)

    def __str__(self):
        return self.value

class FinnaInscription(models.Model):
    value = models.TextField()

    def __str__(self):
        return self.value

class FinnaExhibitionHistory(models.Model):
    value = models.TextField()

    def __str__(self):
        return self.value

class FinnaMaterials(models.Model):
    value = models.TextField()
    lang = models.CharField(max_length=6, null=True, blank=True)

    def __str__(self):
        return self.value

#class FinnaPhysicalDescription(models.Model):
#    value = models.TextField()
#    lang = models.CharField(max_length=6)
#
#    def __str__(self):
#        return self.value


# Managers
class FinnaRecordManager(models.Manager):
    
    # some necessary checks before doing anything else with the record
    def isRecordOk(self, data):

        if ('id' not in data):
            print("ERROR: finna id is missing from data")
            return False
        if ('imageRights' not in data):
            print("ERROR: cannot determine image rights, essential part missing")
            return False
        if 'institutions' not in data:
            print("DEBUG: institution missing, skipping")
            return False
        if ('images' not in data):
            print("no images in the record")
            return False
        if ('imagesExtended' not in data):
            print("no images extended in the record")
            # TODO: if there is no imagesextended, see if there is images?
            return False
        return True
    
    def getEventsValmistus(self, data):
        # TODO: we'll want to check some other fields in this section 
        # so prepare for further changes.. 
        if 'events' not in data:
            return None
            
        # event like where image was taken
        #if 'esitys' in data['events']:
        if 'valmistus' not in data['events']:
            return None
                
        # TODO: there may be multiple sections like this in same record,
        # that might happen when there are multiple images in same record
        if (len(data['events']['valmistus']) == 0):
            return None

        # there may be multiple entries here
        # with type 'esitys' or 'valmistus'
        #for v in data['events']["valmistus"]:
        #    if "type" in v:
        #        valtype = v["type"]
        #        if (valtype == "valmistus"):
        #            return v
        
        return data['events']['valmistus']

    # First try
    # where is that local_data supposed to come from?
    # this is called (indirectly) from finna_search and directly from views.py as well
    # see create_from_finna_record() after this
    #def create_from_data(self, data, local_data={}):
    def create_from_data(self, data):

        def clean_subject_name(subject):
            if isinstance(subject, list):
                if len(subject) == 1:
                    subject = subject[0]
                else:
                    print("Error: Unexpected subject format")
                    print(subject)
                    exit(1)
            return subject

        if (self.isRecordOk(data) == False):
            print("DEBUG: record is not ok, skipping")
            return None

        # Extract and handle institutions data
        institutions = []
        institutions_data = data['institutions']
        for institution in institutions_data:
            #print("DEBUG: institution: ", str(institution))

            # sanitize data: newlines and tabulators into regular spaces at least
            instval = institution['value']
            if (instval.find("\n") > 0 or instval.find("\t") > 0):
                instval = striprepeatespaces(instval)

            itranslated = ""
            if ('translated' in institution):
                itranslated = institution['translated']

            print("using institution", instval, " - ", itranslated)
            r, created = FinnaInstitution.objects.get_or_create(value = instval, 
                                                               defaults={'translated': itranslated})
            institutions.append(r)
            #print("institution saved", instval)
            
            try:
                # Update wikidata id
                wikidata_id = get_institution_wikidata_id(itranslated)
                r.set_wikidata_id(wikidata_id)
                print("using wikidata id ", wikidata_id, " for institution ", itranslated)
            except:
                pass

        #print("parsing collections")

        # Extract and handle collections data

        collectionlist = []
        if 'collections' in data:
            for collection_name in data['collections']:
                
                # cleanup name
                collection_name = striprepeatespaces(collection_name)
                if (len(collection_name) == 0):
                    continue

                # there may be duplicates in some cases?
                if (collection_name in collectionlist):
                    continue
                collectionlist.append(collection_name)

        #print("parsing imagerights")

        # Extract and handle image_right data
        if ('imageRights' not in data):
            print("ERROR: cannot determine image rights, essential part missing")
            print(json.dumps(data))
            exit(1)
        image_rights_data = data['imageRights']
        if ('copyright' not in image_rights_data):
            print("ERROR: cannot determine image rights, essential part missing")
            print(json.dumps(image_rights_data))
            exit(1)
        image_rights_copyright = image_rights_data['copyright']

        image_rights_link = image_rights_data['link']
        image_rights_description = image_rights_data.get('description', '')
        print("DEBUG: found copyright:", image_rights_copyright)

        # TODO:
        # there might be creditLine for some physical objects in some cases
        # this seems to be optional information
        #image_creditline = image_rights_data['creditLine']
        
        # TODO : if description has link to creative commons, replace http:// by https://
        image_right, created = FinnaImageRight.objects.get_or_create(copyright=image_rights_copyright,
                                                                     link=image_rights_link,
                                                                     description=image_rights_description)

        print("imageright added")

        print("creating record instance")
        
        images_data = data['images']
        finna_id = data['id']
        record, created = self.get_or_create(finna_id = finna_id, defaults={'image_right': image_right})
        record.image_right = image_right
        record.number_of_images = len(images_data)

        if ('title' in data):
            record.title = data['title']
        else:
            print("title is missing from data")
            record.title = ""
        if ('shortTitle' in data):
            record.short_title = data['shortTitle']
        else:
            print("short title is missing from data")
            record.short_title = ""
        if ('year' in data):
            record.year = data['year']
            
            # muinasesineitä koskevissa kuvissa voi olla negatiivinen vuosi,
            # joka rikkoo tarkistukset.
            # valokuva ei myöskään voi olla tuolta vuodelta 
            # ja esineitä koskeville vuosille pitäisi olla jokin muu käsittely
            # -> jätetään vuosi pois
            if (int(record.year) < 0):
                print("negative year")
                record.year = None
        else:
            print("no year given in data")
            record.year = None

        # Extract imagesExtended data
        master_url = ""
        master_format = ""

        # TODO: if there isn't "imagesExtended", try "images"
        if ('imagesExtended' in data and len(data['imagesExtended']) > 0):
            images_extended_data = data['imagesExtended']
            if images_extended_data:
                # highResolution may be empty
                if ('highResolution' in images_extended_data[0]
                    and len(images_extended_data[0]['highResolution']) > 0):
                    highres = images_extended_data[0]['highResolution']
                    if ('original' in highres):
                        master_url = highres['original'][0]['url']
                        master_format = highres['original'][0]['format']
                    elif ('master' in highres):
                        master_url = highres['master'][0]['url']
                        master_format = highres['master'][0]['format']
                else:
                    print("WARN: did not find highResolution from imagesExtended")
                    # If no highResolution or original image
                    # might have "master" in addition to "large" as option..
                    master_url = images_extended_data[0]['urls']['large']
                    master_format = 'image/jpeg'
        elif ('images' in data and len(images_data) > 0):
            print("WARN: did not find imagesExtended, using images", images_data[0])
            # might have multiple images here with different index=
            master_url = images_data[0]
            master_format = 'image/jpeg'

        #print("WARN: did not find imagesExtended")
                
        # in some cases, url is not complete:
        # protocol and domain are not stored in the record, which we need later
        if (master_url.find("http://") < 0 and master_url.find("https://") < 0):
            if (master_url.startswith("/Cover/Show") is True):
                master_url = "https://finna.fi" + master_url
            else:
                # might be another museovirasto link, but in different domain
                print("WARN: not a Finna url and not complete url? ", master_url)
        if (master_url == ""):
            # can't use the image without a valid link
            print("ERROR: did not find master url ")
            return False
        # if format is not there it might be possible to determine from extension in resourceName ?

        record.master_url = master_url
        record.master_format = master_format

        if (len(record.finna_id) >= 128):
            print("finna id exceeds maximum length", record.finna_id)
            #print("maximum length currently", record.finna_id.Length())
            return None # skip

        # some images don't have accession numbers (mainly SA-kuva)
        if ('identifierString' in data):
            record.identifier_string = data['identifierString'].strip()

            # identifier string may have list of accession numbers
            if (len(record.identifier_string) > 500):
                print("finna identifier_string exceeds maximum length", record.identifier_string)
                #print("maximum length currently", record.identifier_string.Length())
                return None # skip
        else:
            record.identifier_string = None


        print("parsing nonpresenters")

        # TODO: check for duplicates
        # Extract and handle non_presenter_authors data
        non_presenter_authors = []
        if ('nonPresenterAuthors' in data):
            non_presenter_authors_data = data['nonPresenterAuthors']
            for np_author in non_presenter_authors_data:
                # empty name?
                if ('name' not in np_author):
                    print("name is missing from nonpresenters")
                    continue
                #if ('role' not in np_author):
                #    print("role is missing from nonpresenters")
                #    continue

                authname = np_author['name'].strip()
                authrole = ""
                if ('role' in np_author):
                    authrole = np_author['role'].strip()
                else:
                    print("role is missing from nonpresenters")
                
                r, created = FinnaNonPresenterAuthor.objects.get_or_create(name = authname, role = authrole)
                non_presenter_authors.append(r)
                try:
                    # Update wikidata id
                    wikidata_id = get_author_wikidata_id(authname)
                    r.set_wikidata_id(wikidata_id)
                except:
                    pass

        #print("parsing buildings")

        # Extract and handle buildings data
        buildingslist = []
        if ('buildings' in data):
            buildings_data = data['buildings']
            for building in buildings_data:

                if ('value' not in building):
                    print("value is missing from building")
                    continue
                if ('translated' not in building):
                    print("translated is missing from building")
                    continue
                
                building_value = building['value'].strip()
                building_translated = building['translated'].strip()
                
                r, created = FinnaBuilding.objects.get_or_create(value = building_value, defaults={'translated': building_translated})
                buildingslist.append(r)


        # Extract and handle subjects data
        subjectslist = []
        if ('subjects' in data):
            for subject_name in data['subjects']:
            
                subject_name = clean_subject_name(subject_name)
                if (subject_name not in subjectslist):
                    subjectslist.append(subject_name)

        # Extract and handle subjectPlaces data
        subject_placeslist = []
        if ('subjectPlaces' in data):
            for subject_place_name in data['subjectPlaces']:
                
                subject_place_name = subject_place_name.strip()
                if (subject_place_name not in subject_placeslist):
                    subject_placeslist.append(subject_place_name)
        

        #print("parsing subjectsextended")

        # Extract and handle subjectExtented data
        subjects_extendedlist = []
        if ('subjectsExtended' in data):
            subject_extented_data = data['subjectsExtended']
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

                r, created = FinnaSubjectExtented.objects.get_or_create(heading=heading, 
                                                                        type=se['type'], 
                                                                        record_id=se['id'], 
                                                                        ids=se['ids'], 
                                                                        detail=se['detail'])
                subjects_extendedlist.append(r)

        # Extract and handle subjectActors data
        subject_actorlist = []
        if ('subjectActors' in data):
            for subject_actor_name in data['subjectActors']:
                
                # there is bug in some data: cleanup to avoid further problems
                if (subject_actor_name == None or subject_actor_name == "" or subject_actor_name == "null"):
                    continue

                subject_actor_name = subject_actor_name.strip()
                if (subject_actor_name not in subject_actorlist):
                    subject_actorlist.append(subject_actor_name)
                

        # Extract and handle subjectDetails data
        subject_detailslist = []
        if ('subjectDetails' in data):
            for subject_detail_name in data['subjectDetails']:
                subject_detail_name = subject_detail_name.strip()
                if (subject_detail_name not in subject_detailslist):
                    subject_detailslist.append(subject_detail_name)

        #print("parsing imagesextended")

        print("parsing full record")

        inscriptionlist = []
        exhibitionlist = []
        #classificationlist = []
        summarieslist = []
        alternative_titles = []
        #materiallist = []
        #physical_description_list = []

        # Extract the Summary
        # Data which is stored to separate tables
        if ('fullRecord' not in data):
            print("full record is not given in data")
            
        fullrecord = data['fullRecord']
        xml_root = XEltree.fromstring(fullrecord)
        if (xml_root != None):
            print("found xml in full record")

            # note: should use "inscriptions" in commons template?
            fiobj = FinnaInscription.objects
            inscriptions = xml_root.findall(".//inscriptionDescription/descriptiveNoteValue")
            for ins in inscriptions:
                #inslang = ins.get("lang") 
                instext = ins.text
                if (instext == None):
                    print("DEBUG: skipping inscriptions as null")
                    continue
                print("DEBUG: found inscriptions:", instext)
                r, created = fiobj.get_or_create(value = instext)
                inscriptionlist.append(r)

            # some of these might be better in physical descriptions?
            # <objectDescriptionSet type="description"><descriptiveNoteValue lang="fi" label="kuvaus">fyysinen kuvaus: vaaka
            fsobj = FinnaSummary.objects
            # should use more precise path..
            # // objectDescriptionSet, label = "description" or type = "description"
            descriptive_notes = xml_root.findall(".//objectDescriptionSet/descriptiveNoteValue")
            for note in descriptive_notes:
                notelang = note.get("lang") 
                notelabel = note.get("label") # "kuvaus"
                notetext = note.text
                if (notelang == None or notetext == None):
                    print("DEBUG: skipping descriptive note as null")
                    continue
                #if (notelabel != "kuvaus"):
                # something else..
                print("DEBUG: found descnote:", notetext)
                summary, created = fsobj.get_or_create(
                                                 text = notetext,
                                                 lang = notelang,
                                                 defaults = {'order': 1})
                summarieslist.append(summary)

            fatobj = FinnaAlternativeTitle.objects
            # shoud use //titleSet/appellationValue for this purpose 
            # there is also ex. nameActorSet/appellationValue, legalBodyName/appellationValue etc.
            appellations = xml_root.findall(".//titleSet/appellationValue")
            for app in appellations:
                applang = app.get("lang") 
                applabel = app.get("label") # "nimi"
                apppref = app.get("pref") # "alternate"
                apptext = app.text
                if (applang == None or applabel == None or apppref == None or apptext == None):
                    print("DEBUG: skipping appellation as null")
                    continue
                #if (apppref != "alternate" or applabel != "nimi"):
                # something else..
                print("DEBUG: found appellation:", apptext)
                alt_title, created = fatobj.get_or_create(text = apptext,
                                                    lang = applang,
                                                    pref = apppref)
                alternative_titles.append(alt_title)

            fehobj = FinnaExhibitionHistory.objects
            # related work: publications of the item such as newspapre or magazine
            # should use "exhibition history" in commons template
            related_works = xml_root.findall(".//relatedWork/displayObject")
            for work in related_works:
                #worklang = work.get("lang") # note: does not exist usually where we want it..
                worklabel = work.get("label") 
                worktext = work.text
                if (worklabel == None or worktext == None):
                    print("DEBUG: skipping related work as null")
                    continue
                if (worklabel != "julkaisu"):
                    # something else
                    continue
                print("DEBUG: found related work:", worktext)
                r, created = fehobj.get_or_create(value = worktext)
                exhibitionlist.append(r)

            #fclobj = FinnaClassifications.objects
            # TODO: parse classification><term lang="fi" label="luokitus"
            # has information like >mustavalkoinen  negatiivi< that we can further categorize with later
            # some of same information may be in objectDescriptionSet><descriptiveNoteValue with "ominaisuudet" 
            #classifications = xml_root.findall(".//classification/term")
            #for cls in classifications:
            #    clslang = cls.get("lang") 
            #    clslabel = cls.get("label") # "luokitus" or "classification"
            #    clstext = cls.text
            #    if (clslabel == None or clstext == None):
            #        print("DEBUG: skipping classification as null")
            #        continue
            #    if (clslabel != "luokitus"):
                    # something else
            #        continue
                # in this case, should have two separate terms with values like "lasinegatiivi" and ">mustavalkoinen  negatiivi"
            #    print("DEBUG: found classification:", clstext)
            #    r, created = fclobj.get_or_create(value = clstext, lang = clslang)
            #    classificationlist.append(r)
            
            # termMaterialsTech/term
            # materialsTech/termMaterialsTech/conceptID/term
            # or FinnaMaterials..create()
            # or materiallist.append() ?
            #materials = xml_root.findall(".//materialsTech/termMaterialsTech")
            
            # objectMeasurementsSet><displayObjectMeasurements
            #fpdobj = FinnaPhysicalDescription.objects
            #omeasurements = xml_root.findall(".//objectMeasurementsSet/displayObjectMeasurements")
            #for oms in omeasurements:
            #    omslang = oms.get("lang") 
            #    omstext = oms.text
            #    if (omslang == None or omstext == None):
            #        print("DEBUG: skipping object measurement as null")
            #        continue
            #    print("DEBUG: found object measurement:", omstext)
            #    r, created = fpdobj.get_or_create(value = omstext, lang = omslang)
            #    physical_description_list.append(r)

            print("done with xml in full record")
        else:
            print("could not parse xml full record")

        if ('measurements' in data):
            measurements = data['measurements']
            measurementlist = []
            for m in measurements:
                m = striprepeatespaces(m)
                measurementlist.append(m)
            record.measurements = "\n".join(measurementlist)

        valmistus = self.getEventsValmistus(data)
        if (valmistus != None):
            
            # event like where image was taken
            #if 'esitys' in data['events']:
            
            # there may be multiple entries
            
            for valm in valmistus:
                if ('type' in valm):
                    # may have events of different types
                    vtype = valm['type']
                    if (vtype == 'esitys'):
                        continue
                    if (vtype != "valmistus"):
                        print("unknown type", vtype)
                        continue
                print("DEBUG: valmistus", str(valm))
                
                if ('date' in valm):
                    # remove extra whitespaces if any:
                    # cleanup the data a bit
                    # also cleanup newlines and tabulators within (if any)
                    vdate = striprepeatespaces(valm['date'])

                    if (len(vdate) > 0):
                        record.date_string = vdate
                        print('keeping date_string ', vdate)

                if ('places' in valm):
                    for place in valm['places']:
                        # check the data, might be a dict() instead of plain string
                        # as there might be some data structure in some cases

                        ptmp = ""
                        if isinstance(place, dict):
                            print("DEBUG: place is dict", str(place))
                            if ("placeName" in place):
                                print("DEBUG: found placename", str(place["placeName"]))
                                ptmp = place["placeName"].strip()
                        else:
                            print("DEBUG: found place string", str(place))
                            ptmp = place.strip()
                        
                        ptmp = striprepeatespaces(ptmp)
                        if (ptmp not in subject_placeslist):
                            subject_placeslist.append(ptmp)

                #if ('materials' in valm):
                #    for material in valm['materials']:
                #        material = striprepeatespaces(material)
                #        materiallist.append(material)
                #if ('materialsExtended' in valm):
                #    for material in valm['materialsExtended']:
                #if ('methods' in valm):
                #    for method in valm['methods']:
                #if ('methodsExtended' in valm):
                #    for method in valm['methodsExtended']:
                            

        if (record.date_string == None):
            print('Note: no date_string in ', record.finna_id)
            # should not be null?
            #record.date_string = ""

        print("Setting information to record..")

        record.summaries.clear()
        for summary in summarieslist:
            record.summaries.add(summary)

        #record.classifications.clear()
        #for i in classificationlist:
        #    record.classifications.add(i)

        record.inscriptions.clear()
        for i in inscriptionlist:
            record.inscriptions.add(i)
            
        record.exhibition_history.clear()
        for i in exhibitionlist:
            record.exhibition_history.add(i)

        # materials and physical object descriptions might use same..
        #record.materials.clear()
        #for material in materiallist:
        #    r, created = FinnaMaterials.objects.get_or_create(value = material)
        #    record.materials.add(r)

        #record.physical_descriptions.clear()
        #for i in physical_description_list:
        #    record.physical_descriptions.add(i)

        record.alternative_titles.clear()
        for alternative_title in alternative_titles:
            record.alternative_titles.add(alternative_title)

        for non_presenter_author in non_presenter_authors:
            record.non_presenter_authors.add(non_presenter_author)

        for building in buildingslist:
            record.buildings.add(building)

        for subject_name in subjectslist:
            if (subject_name == None or subject_name == "" or subject_name == "null"):
                continue

            r, created = FinnaSubject.objects.get_or_create(name = subject_name.strip())
            record.subjects.add(r)

        for subject_place_name in subject_placeslist:
            if (subject_place_name == None or subject_place_name == "" or subject_place_name == "null"):
                continue
            
            r, created = FinnaSubjectPlace.objects.get_or_create(name = subject_place_name)
            record.subject_places.add(r)

        for se in subjects_extendedlist:
            record.subject_extented.add(se)

        for subject_actor_name in subject_actorlist:
            if (subject_actor_name == None or subject_actor_name == "" or subject_actor_name == "null"):
                continue

            r, created = FinnaSubjectActor.objects.get_or_create(name = subject_actor_name)
            record.subject_actors.add(r)
            try:
                # Update wikidata id
                wikidata_id = get_subject_actors_wikidata_id(subject_actor_name)
                r.set_wikidata_id(wikidata_id)
            except:
                pass


        for subject_detail in subject_detailslist:
            
            r, created = FinnaSubjectDetail.objects.get_or_create(name = subject_detail)
            record.subject_details.add(r)

        for collection_name in collectionlist:
            if (collection_name == None or collection_name == ""):
                continue
            
            print("using collection", collection_name)
            r, created = FinnaCollection.objects.get_or_create(name = collection_name)
            record.collections.add(r)
        
            try:
                # TODO: search collection with institution
                # since collection names are not unique
                #wikidata_id = get_collection_wikidata_id(institution.wikidata_id, collection.name)
                
                # Update wikidata id
                wikidata_id = get_collection_wikidata_id(collection_name)
                r.set_wikidata_id(wikidata_id)
                print("using wikidata id ", wikidata_id, " for collection ", collection_name)
            except:
                pass

        for institution in institutions:
            record.institutions.add(institution)

        try:
            print("creating search index")
            search_index, created = FinnaRecordSearchIndex.objects.get_or_create(datatext=str(data))
            record.data = search_index
        except:
            print('Error creating search index for record')
            return None

        try:
            print("saving record instance")
            record.save()
        except DataError as e:
            print('Error: {}'.format(e))
            exit(1)

        return record

    # try to improve debuggability at least a bit
    # called from finna_search.py/import_helper.py
    # where is that local_data supposed to come from?
    #def create_from_finna_record(self, record, local_data={}):
    def create_from_finna_record(self, record):
            
        # TODO: parse and validate first before trying to store it..
        if (self.isRecordOk(record) == False):
            print("DEBUG: record is not ok, skipping")
            return False

        with transaction.atomic():

            try:
                #ret = self.create_from_data(record, local_data)
                ret = self.create_from_data(record)
                if (ret != None):
                    print(f'{ret.id} {ret.finna_id} {ret.title} saved')
                else:
                    print("record was skipped ")

            except Error as e:
                print('Error: {}'.format(e))
                return False # stop there
            except:
                print("ERROR saving record: ")
                print(record)
                # just skip for now
                return False # stop there
        return True

    # this was part of create_record() but nothing seems to use it,
    # move it here anyway in case there is some use for it
    def add_local_data(self, finna_image, local_data={}):

        # Extract local add_categories data
        # TODO: why is this using "local_data" instead of record? where is local_data filled?
        add_categories_data = local_data.pop('add_categories', [])
        add_categories = [FinnaLocalSubject.objects.get_or_create(value=value)[0] for value in add_categories_data]


        # TODO: why is this using "local_data" instead of record? where is local_data filled?
        add_depicts_data = local_data.pop('add_depicts', [])
        add_depicts = [FinnaLocalSubject.objects.get_or_create(value=value)[0] for value in add_depicts_data]

        #finna_image.add_categories.clear()
        #for add_category in add_categories:
        #    finna_image.add_categories.add(add_category)

        #finna_image.add_depicts.clear()
        #for add_depict in add_depicts:
        #    finna_image.add_depicts.add(add_depict)


class FinnaRecordSearchIndex(models.Model):
    datatext = models.TextField()


class FinnaImage(models.Model):
    objects = FinnaRecordManager() # why does this refer to top-level "manager" ? hierarchy is backwards here..

    finna_id = models.CharField(max_length=200, null=False, blank=False, db_index=True, unique=True)
    title = models.TextField()
    alternative_titles = models.ManyToManyField(FinnaAlternativeTitle)
    year = models.PositiveIntegerField(unique=False, null=True, blank=True)
    date_string = models.TextField()
    number_of_images = models.PositiveIntegerField(unique=False, null=True, blank=True)
    master_url = models.URLField(max_length=500)
    master_format = models.TextField()
    measurements = models.TextField()
    materials = models.ManyToManyField(FinnaMaterials)
    non_presenter_authors = models.ManyToManyField(FinnaNonPresenterAuthor)
    summaries = models.ManyToManyField(FinnaSummary)
    subjects = models.ManyToManyField(FinnaSubject)
    subject_extented = models.ManyToManyField(FinnaSubjectExtented)
    subject_places = models.ManyToManyField(FinnaSubjectPlace)
    subject_actors = models.ManyToManyField(FinnaSubjectActor)
    subject_details = models.ManyToManyField(FinnaSubjectDetail)
    classifications = models.ManyToManyField(FinnaClassifications)
    inscriptions = models.ManyToManyField(FinnaInscription)
    exhibition_history = models.ManyToManyField(FinnaExhibitionHistory)
    #physical_descriptions = models.ManyToManyField(FinnaPhysicalDescription)
    collections = models.ManyToManyField(FinnaCollection)
    buildings = models.ManyToManyField(FinnaBuilding)
    institutions = models.ManyToManyField(FinnaInstitution)
    image_right = models.ForeignKey(FinnaImageRight, on_delete=models.RESTRICT)
    add_categories = models.ManyToManyField(FinnaLocalSubject, related_name="category_images") # rename to "local subjects" or something..
    add_depicts = models.ManyToManyField(FinnaLocalSubject, related_name="depict_images") # rename to "local subjects" or something..
    best_wikidata_location = models.ManyToManyField(FinnaSubjectWikidataPlace)
    commons_images = models.ManyToManyField(WikimediaCommonsImage)
    already_in_commons = models.BooleanField(default=False)
    skipped = models.BooleanField(default=False)
    data = models.ForeignKey(FinnaRecordSearchIndex, on_delete=models.RESTRICT, null=True, blank=True)

    # Accession number or similar identifier
    # note that this can be array of short identifiers (accession numbers) in some collections
    identifier_string = models.CharField(max_length=500, null=True, blank=True)
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
    def filename_extension(self):
        if (self.master_format == None):
            print("format missing for file extension")
            exit(1)
        if (self.master_format == ""):
            print("format missing for file extension")
            exit(1)
        
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
