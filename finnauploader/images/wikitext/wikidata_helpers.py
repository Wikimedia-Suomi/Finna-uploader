# for queries from wikidata-context
#
# these get called from photographer.py, sdc_helpers.py,
# categories.py and models.py
#
# during generating data for upload

from images.models_mappingcache import SubjectPlacesCache, \
                                       CollectionsCache, \
                                       InstitutionsCache, \
                                       NonPresenterAuthorsCache, \
                                       SubjectActorsCache

from images.exceptions import MissingNonPresenterAuthorError, \
                              MultipleNonPresenterAuthorError, \
                              MissingSubjectActorError

import time
import pywikibot

# reduce repeated queries a bit
institutionNames = {}
creatorNames = {}
subjectCategories = {}


# if there is update, just invalidate all
def invalidateWikidataCaches():
    institutionNames.clear()
    creatorNames.clear()
    subjectCategories.clear()


def get_institution_name(institutions):
    if len(institutions) != 1:
        print('incorrect number of institutions')
        exit(1)

    for institution in institutions:
        institution_name = institution['value']
        obj = InstitutionsCache.objects.get(name=institution_name)
        if obj:
            return institution_name

    print("Unknown institution: " + str(institutions))
    url = 'https://commons.wikimedia.org/wiki/User:FinnaUploadBot/data/institutions' # noqa
    print(f'Missing in {url}')
    exit(1)


# Allowed --collections values
# See also finna.py: do_finna_search()
def get_collection_names():
    default_collections = [
                  'Kuvasiskot',
                  'Studio Kuvasiskojen kokoelma',
                  'JOKA',
                  'JOKA Journalistinen kuva-arkisto',
                  'SA-kuva',
                  'Kansallisgalleria Ateneumin taidemuseo'
                  ]

    collections = CollectionsCache.objects.all()
    collection_names = [collection.name for collection in collections]
    return collection_names if collection_names else default_collections


# Shortcut -> long-name translations
def get_collection_name_from_alias(name):
    aliases = {
             'Kuvasiskot': 'Studio Kuvasiskojen kokoelma',
             'JOKA': 'JOKA Journalistinen kuva-arkisto',
             'SA-kuva': '0/SA-kuva/',
             'Kansallisgalleria Ateneumin taidemuseo':
             '0/Kansallisgalleria Ateneumin taidemuseo/'
    }
    if name in aliases:
        return aliases[name]
    else:
        return name


def get_subject_place_wikidata_id(location_string):
    try:
        place = SubjectPlacesCache.objects.get(name=location_string)
        return place.wikidata_id
    except:
        return None


# use mapping from Finna-string to qcode
def get_collection_wikidata_id(name):

    # Remove extra whitespaces from name
    name = name.strip()

    obj = CollectionsCache.objects.filter(name=name).first()
    if obj:
        return obj.wikidata_id

    print(f'Unknown collection: "{name}"')
    exit(1)


# use mapping from Finna-string to qcode
def get_institution_wikidata_id(institution_name):
    obj = InstitutionsCache.objects.get(name=institution_name)
    if obj:
        return obj.wikidata_id

    print("Unknown institution: " + str(institution_name))
    exit(1)


def setInstitutionName(wikidata_id, name):
    institutionNames[wikidata_id] = name


def getInstitutionName(wikidata_id):
    if (wikidata_id in institutionNames):
        return institutionNames[wikidata_id]
    return None


def isInstitutionName(wikidata_id):
    if (wikidata_id in institutionNames):
        return True
    return False


def get_institution_name_by_wikidata_id(wikidata_id):

    # reduce repeated queries a bit
    if (isInstitutionName(wikidata_id) is True):
        institution_template_name = getInstitutionName(wikidata_id)
        return institution_template_name

    # Connect to Wikidata
    site = pywikibot.Site("wikidata", "wikidata")
    repo = site.data_repository()

    # Access the Wikidata item using the provided ID
    item = pywikibot.ItemPage(repo, wikidata_id)

    # If the item doesn't exist, return None
    if not item.exists():
        print(f"Item {wikidata_id} does not exist!")
        exit(1)

    # Try to fetch the value of the property P1472 (Commons Creator page)
    claims = item.get().get('claims')

    if 'P1612' in claims:
        institution_page_claim = claims['P1612'][0]
        institution_template_name = institution_page_claim.getTarget()

        # reduce repeated queries a bit
        setInstitutionName(wikidata_id, institution_template_name)

        return institution_template_name
    else:
        print(f"Item {wikidata_id} does not exist!")
        exit(1)


def get_author_name(nonPresenterAuthors):
    ret = None
    for nonPresenterAuthor in nonPresenterAuthors:
        name = nonPresenterAuthor['name']
        # not used
        # role = nonPresenterAuthor['role']

        if (nonPresenterAuthor.is_photographer()):
            obj = NonPresenterAuthorsCache.objects.get(name=name)
            if obj:
                if not ret:
                    ret = name
                else:
                    raise MultipleNonPresenterAuthorError
            else:
                url =  'https://commons.wikimedia.org/wiki/User:FinnaUploadBot/data/nonPresenterAuthors' # noqa
                print(f'Name {name} is missing from {url}')
                raise MissingNonPresenterAuthorError

    if not ret:
        url = 'https://commons.wikimedia.org/wiki/User:FinnaUploadBot/data/nonPresenterAuthors' # noqa
        print(f'Unknown author. Add it to the {url}')
        print(nonPresenterAuthors)
        raise MissingNonPresenterAuthorError

    return ret


# use mapping from Finna-string to qcode
def get_author_wikidata_id(name):
    try:
        obj = NonPresenterAuthorsCache.objects.get(name=name)
        return obj.wikidata_id
    except NonPresenterAuthorsCache.DoesNotExist:
        url = 'https://commons.wikimedia.org/wiki/User:FinnaUploadBot/data/nonPresenterAuthors' # noqa
        print(f'Unknown author: "{name}". Add author to {url}')

        # Exit may throw a error so little sleep so user can read the message
        time.sleep(10)
        exit(1)


def setCreatorName(wikidata_id, name):
    creatorNames[wikidata_id] = name


def getCreatorName(wikidata_id):
    if (wikidata_id in creatorNames):
        return creatorNames[wikidata_id]
    return None


def isCreatorName(wikidata_id):
    if (wikidata_id in creatorNames):
        return True
    return False


# creator name according wikidata entry for creator template
def get_creator_nane_by_wikidata_id(wikidata_id):

    # reduce repeated queries a bit
    if (isCreatorName(wikidata_id) is True):
        creator_name = getCreatorName(wikidata_id)
        return creator_name

    # Connect to Wikidata
    site = pywikibot.Site("wikidata", "wikidata")
    repo = site.data_repository()

    # Access the Wikidata item using the provided ID
    item = pywikibot.ItemPage(repo, wikidata_id)

    # If the item doesn't exist, return None
    if not item.exists():
        print(f"Item {wikidata_id} does not exist!")
        return None

    # Try to fetch the value of the property P1472 (Commons Creator page)
    # Creator-tekijämalline Wikimedia Commonsissa (P1472)

    claims = item.get().get('claims')

    if 'P1472' in claims:
        creator_page_claim = claims['P1472'][0]
        creator_name = creator_page_claim.getTarget()

        # reduce repeated queries a bit
        setCreatorName(wikidata_id, creator_name)

        return creator_name
    else:
        return None


def isCategoryExistingInCommons(commons_site, category_name):
    if (category_name.find("Category:") < 0):
        category_name = "Category:" + category_name

    photo_category = pywikibot.Category(commons_site, category_name)

    # Check if the category exists
    if photo_category.exists():
        return True
    return False


def setSubjectCategory(wikidata_id, name):
    subjectCategories[wikidata_id] = name


def getSubjectCategory(wikidata_id):
    if (wikidata_id in subjectCategories):
        return subjectCategories[wikidata_id]
    return None


def isSubjectCategory(wikidata_id):
    if (wikidata_id in subjectCategories):
        return True
    return False


# Commons-category associated with wikidata-entry
# Commons-luokka (P373)
def get_subject_image_category_from_wikidata_id(wikidata_id, mandatory=False):

    # reduce repeated queries a bit
    # if (isSubjectCategory(wikidata_id) is True):
    #    return getSubjectCategory(wikidata_id)

    # Connect to Wikidata
    site = pywikibot.Site("wikidata", "wikidata")
    # commons_site = pywikibot.Site("commons", "commons")
    repo = site.data_repository()

    item = None
    try:
        # Access the Wikidata item using the provided ID
        item = pywikibot.ItemPage(repo, wikidata_id)
    except:
        # at least try to tell what is missing
        print(f'Item for Wikidata ID {wikidata_id} is missing')
        raise

    # If the item doesn't exist, return None
    if not item.exists():
        print(f"Item {wikidata_id} does not exist!")
        return None

    # Try to fetch the value of the property P373 (Commons category)
    claims = item.get().get('claims')

    if 'P373' in claims:
        commons_category_claim = claims['P373'][0]
        category_name = commons_category_claim.getTarget()
        print(category_name)

        # reduce repeated queries a bit
        setSubjectCategory(wikidata_id, category_name)
        return category_name

        # photo_category = pywikibot.Category(commons_site, category_name)

        # Check if the category exists
        # this is pointless: you can't have non-existing categories in wikidata? # noqa
        # also, you can generate various sub-categories based on this..
        # if photo_category.exists():
        #     category_name = photo_category.title()
        #     reduce repeated queries a bit
        #     setSubjectCategory(wikidata_id, category_name)
        #     return category_name

    if mandatory:
        print(f'ERROR: Commons P373 category in https://wikidata.org/wiki/{wikidata_id} is missign.') # noqa
        exit(1)
    return None


class WikidataPlace:
    def __init__(self):
        self.category_name = None
        self.instance_of = None
        self.part_of = None
        self.region = None
        self.nation = None


def get_place_by_wikidata_id(wikidata_id):

    # reduce repeated queries a bit
    # if (isPlaceCategory(wikidata_id) is True):
    #     return getPlaceCategory(wikidata_id)

    # Connect to Wikidata
    site = pywikibot.Site("wikidata", "wikidata")
    # commons_site = pywikibot.Site("commons", "commons")
    repo = site.data_repository()

    item = None
    try:
        # Access the Wikidata item using the provided ID
        item = pywikibot.ItemPage(repo, wikidata_id)
    except:
        # at least try to tell what is missing
        print(f'Item for Wikidata ID {wikidata_id} is missing')
        raise

    # If the item doesn't exist, return None
    if not item.exists():
        print(f"Item {wikidata_id} does not exist!")
        return None

    # Try to fetch the value of the property P373 (Commons category)
    claims = item.get().get('claims')

    wdp = WikidataPlace()

    # commons category for this place (if any)
    if 'P373' in claims:
        commons_category_claim = claims['P373'][0]
        wdp.category_name = commons_category_claim.getTarget()

    # verify for type of city/place to live
    if 'P31' in claims:
        wdp.instance_of = claims['P31'][0]

    # part of some division (maakunta) ?
    if 'P361' in claims:
        wdp.part_of = claims['P361'][0]

    # sijaitsee hallinnollisessa alueyksikössä (P131)
    if 'P131' in claims:
        wdp.region = claims['P131'][0]

    # valtio (P17)
    if 'P17' in claims:
        wdp.nation = claims['P17'][0]

    return wdp


def get_subject_actors_wikidata_ids(subjectActors):
    ret = []
    for subjects_actor_name in subjectActors:
        obj = SubjectActorsCache.objects.get(name=subjects_actor_name)
        if obj:
            ret.append(obj.wikidata_id)
        else:
            url = 'https://commons.wikimedia.org/wiki/User:FinnaUploadBot/data/subjectActors' # noqa
            print('Error: Unknown actor "{subjectActor}". Add actor to {url}')
            raise MissingSubjectActorError
    return ret


def get_subject_actors_wikidata_id(name):
    obj = SubjectActorsCache.objects.get(name=name)
    if obj:
        return obj.wikidata_id
    else:
        url = 'https://commons.wikimedia.org/wiki/User:FinnaUploadBot/data/subjectActors' # noqa
        print(f'Error: Unknown actor "{name}". Add actor to {url}')
        raise MissingSubjectActorError


pywikibot.config.socket_timeout = 120
site = pywikibot.Site("commons", "commons")  # for Wikimedia Commons
site.login()
