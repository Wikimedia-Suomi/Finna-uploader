from watson import search as watson
from django.db import models
from django.db import transaction
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.db.utils import DataError
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

#class FinnaPhysicalDescription(models.Model):
#    value = models.TextField()
#    lang = models.CharField(max_length=6)
#
#    def __str__(self):
#        return self.value


# Managers
class FinnaRecordManager(models.Manager):

    # First try
    # where is that local_data supposed to come from?
    # this is called (indirectly) from finna_search and directly from views.py as well
    # see create_from_finna_record() after this
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

        #print("parsing institutions")

        # Extract and handle institutions data
        institutions = []
        institutions_data = data.pop('institutions', [])
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
        # TODO: check for duplicates?

        collections = []
        collections_data = data.pop('collections', [])
        for collection_name in collections_data:
            
            # cleanup name
            collection_name = striprepeatespaces(collection_name)
            
            print("using collection", collection_name)
            r, created = FinnaCollection.objects.get_or_create(name = collection_name)
            collections.append(r)
            #print("collection saved", collection_name)
        
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


        #print("parsing nonprepsenters")

        # TODO: check for duplicates
        # Extract and handle non_presenter_authors data
        non_presenter_authors = []
        non_presenter_authors_data = data.pop('nonPresenterAuthors', [])
        for np_author in non_presenter_authors_data:
            authname = np_author['name'].strip()
            authrole = np_author['role'].strip()
            
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
        buildings = []
        buildings_data = data.pop('buildings', [])
        for building in buildings_data:
            
            building_value = building['value'].strip()
            building_translated = building['translated'].strip()
            
            r, created = FinnaBuilding.objects.get_or_create(value = building_value, defaults={'translated': building_translated})
            buildings.append(r)


        # Extract and handle subjects data
        subjects = []
        subjects_data = data.pop('subjects', [])
        for subject_name in subjects_data:
            
            subject_name = clean_subject_name(subject_name)
            
            r, created = FinnaSubject.objects.get_or_create(name = subject_name.strip())
            subjects.append(r)


        # Extract and handle subjectPlaces data
        subject_places = []
        subject_places_data = data.pop('subjectPlaces', [])
        for subject_place_name in subject_places_data:
            
            subject_place_name = subject_place_name.strip()
            
            r, created = FinnaSubjectPlace.objects.get_or_create(name = subject_place_name)
            subject_places.append(r)


        #print("parsing subjectsextended")

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

            r, created = FinnaSubjectExtented.objects.get_or_create(heading=heading, 
                                                                    type=se['type'], 
                                                                    record_id=se['id'], 
                                                                    ids=se['ids'], 
                                                                    detail=se['detail'])
            subject_extented.append(r)

        # Extract and handle subjectActors data
        subject_actors = []
        subject_actors_data = data.pop('subjectActors', [])
        for subject_actor_name in subject_actors_data:
            
            # there is bug in some data: cleanup to avoid further problems
            if (subject_actor_name == None or subject_actor_name == "" or subject_actor_name == "null"):
                continue

            subject_actor_name = subject_actor_name.strip()
            
            act, created = FinnaSubjectActor.objects.get_or_create(name = subject_actor_name)
            subject_actors.append(act)
            try:
                # Update wikidata id
                wikidata_id = get_subject_actors_wikidata_id(subject_actor_name)
                act.set_wikidata_id(wikidata_id)
            except:
                pass

        # Extract and handle subjectDetails data
        subject_details = []
        subject_details_data = data.pop('subjectDetails', [])
        for subject_detail_name in subject_details_data:
            
            subject_detail_name = subject_detail_name.strip()
            
            r, created = FinnaSubjectDetail.objects.get_or_create(name = subject_detail_name)
            subject_details.append(r)


        #print("parsing imagerights")

        # TODO:
        # there might be creditLine for some physical objects in some cases
        
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

        #print("parsing imagesextended")

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

        #print("parsing full record")

        inscriptionlist = []
        exhibitionlist = []
        classificationlist = []
        summarieslist = []
        alternative_titles = []
        #physical_description_list = []

        # Extract the Summary
        # Data which is stored to separate tables
        fullrecord = data['fullRecord']
        xml_root = XEltree.fromstring(fullrecord)
        if (xml_root != None):

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

            fclobj = FinnaClassifications.objects
            # TODO: parse classification><term lang="fi" label="luokitus"
            # has information like >mustavalkoinen  negatiivi< that we can further categorize with later
            # some of same information may be in objectDescriptionSet><descriptiveNoteValue with "ominaisuudet" 
            classifications = xml_root.findall(".//classification/term")
            for cls in classifications:
                clslang = cls.get("lang") 
                clslabel = cls.get("label") # "luokitus" or "classification"
                clstext = cls.text
                if (clslabel == None or clstext == None):
                    print("DEBUG: skipping classification as null")
                    continue
                if (clslabel != "luokitus"):
                    # something else
                    continue
                # in this case, should have two separate terms with values like "lasinegatiivi" and ">mustavalkoinen  negatiivi"
                print("DEBUG: found classification:", clstext)
                r, created = fclobj.get_or_create(value = clstext, lang = clslang)
                classificationlist.append(r)
                
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


        # Extract local add_categories data
        # TODO: why is this using "local_data" instead of record? where is local_data filled?
        add_categories_data = local_data.pop('add_categories', [])
        add_categories = [FinnaLocalSubject.objects.get_or_create(value=value)[0] for value in add_categories_data]


        # TODO: why is this using "local_data" instead of record? where is local_data filled?
        add_depicts_data = local_data.pop('add_depicts', [])
        add_depicts = [FinnaLocalSubject.objects.get_or_create(value=value)[0] for value in add_depicts_data]

        print("creating record instance")

        # TODO: move this earlier so we can do away with temporary holders..
        # Create the record instance
        record, created = self.get_or_create(finna_id=data['id'], defaults={'image_right': image_right})
        record.title = data.get('title', '')
        record.short_title = data.get('shortTitle', '')
        record.identifier_string = data.pop('identifierString', None)
        record.year = data.pop('year', None)
        record.number_of_images = len(images_data)
        record.master_url = master_url
        record.master_format = master_format
        record.measurements = "\n".join(data['measurements'])
        
        if (len(record.finna_id) >= 128):
            print("finna id exceeds maximum length", record.finna_id)
            #print("maximum length currently", record.finna_id.Length())
            return None # skip
        
        # some images don't have accession numbers (mainly SA-kuva)
        if (record.identifier_string != None):
            record.identifier_string = record.identifier_string.strip()
            # identifier string may have list of accession numbers
            if (len(record.identifier_string) > 500):
                print("finna identifier_string exceeds maximum length", record.identifier_string)
                #print("maximum length currently", record.identifier_string.Length())
                return None # skip

        # TODO: we'll want to check some other fields in this section 
        # so prepare for further changes.. 
        if 'events' in data:
            if 'valmistus' in data['events']:
                
                # TODO: there may be multiple sections like this in same record,
                # that might happen when there are multiple images in same record
                if (len(data['events']['valmistus']) > 0):
                    
                    #for v in data['events']['valmistus']:
                    valm = data['events']['valmistus'][0]
                    if ('date' in valm):
                        # remove extra whitespaces if any:
                        # cleanup the data a bit
                        # also cleanup newlines and tabulators within (if any)
                        vdate = striprepeatespaces(valm['date'])

                        if (len(vdate) > 0):
                            record.date_string = vdate
                            print('keeping date_string ', vdate)
                    
        if (record.date_string == None):
            print('Note: no date_string in ', record.finna_id)

        record.summaries.clear()
        for summary in summarieslist:
            record.summaries.add(summary)

        record.classifications.clear()
        for i in classificationlist:
            record.classifications.add(i)

        record.inscriptions.clear()
        for i in inscriptionlist:
            record.inscriptions.add(i)
            
        record.exhibition_history.clear()
        for i in exhibitionlist:
            record.exhibition_history.add(i)

        #record.physical_descriptions.clear()
        #for i in physical_description_list:
        #    record.physical_descriptions.add(i)

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
            # there are emoty entries in some cases, which end is the reason?
            if (subject_actor != None):
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
    # called from finna_search.py
    # where is that local_data supposed to come from?
    def create_from_finna_record(self, record, local_data={}):
            
        # TODO: parse and validate first before trying to store it..

        with transaction.atomic():
            try:
                ret = self.create_from_data(record, local_data)
                if (ret != None):
                    print(f'{ret.id} {ret.finna_id} {ret.title} saved')
                else:
                    print("record was skipped ")
                    
            except:
                print("ERROR saving record: ")
                print(record)
                # just skip for now
                #return False
        return True


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
