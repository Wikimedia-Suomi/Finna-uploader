import pywikibot
import re

def parse_name_and_q_item(text):
    pattern = r'\*\s(.*?)\s:\s\{\{Q\|(Q\d+)\}\}'
    matches = re.findall(pattern, text)

    # Extracted names and Q-items
    parsed_data = {}
    for name, q_item in matches:
        parsed_data[name] = q_item
    return parsed_data

def get_institution_name(institutions):
    if len(institutions)!=1:
        print('incorrect number of institutions')
        exit(1)
    for institution in institutions:
        if institution['value'] in institutionsCache:
            return institution['value']
   
    print("Unknown institution: " + str(institutions))
    print("Missing in https://commons.wikimedia.org/wiki/User:FinnaUploadBot/data/institutions")
    exit(1) 

def get_collection_wikidata_id(name):
    if name in collectionsCache:
        return collectionsCache[name]
    print("Unknown collection: " + str(name))
    exit(1)
        
def get_institution_wikidata_id(institution_name):
    if institution_name in institutionsCache:
        return institutionsCache[institution_name]
    print("Unknown institution: " + str(institutions))
    exit(1)

def get_institution_template_from_wikidata_id(wikidata_id):
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
        return '{{Institution:' + institution_template_name + '}}'
    else:
        print(f"Item {wikidata_id} does not exist!")
        exit(1)
        
def get_author_name(nonPresenterAuthors):
    ret = None
    for nonPresenterAuthor in nonPresenterAuthors:
        name = nonPresenterAuthor['name']
        role = nonPresenterAuthor['role']
        
        if role == "kuvaaja":
            if name in nonPresenterAuthorsCache:
                if not ret:
                    ret=name
                else:
                    print("Multiple authors")
                    print(nonPresenterAuthors)
                    exit(1)
            else:
                print(f'Name {name} is missing from https://commons.wikimedia.org/wiki/User:FinnaUploadBot/data/nonPresenterAuthors')
                
    if not ret: 
        print("Unknown author")
        print(nonPresenterAuthors)
        exit(1)
        
    return ret
    
def get_author_wikidata_id(name):
    if name in nonPresenterAuthorsCache:
        wikidata_id=nonPresenterAuthorsCache[name]
        return wikidata_id
    else:
        print(f'Unknown author: {author_name}')
        exit(1)

def get_creator_template_from_wikidata_id(wikidata_id):
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
    claims = item.get().get('claims')
    
    if 'P1472' in claims:
        creator_page_claim = claims['P1472'][0]
        creator_template_name = creator_page_claim.getTarget()
        return '{{Creator:' + creator_template_name + '}}'
    else:
        return None

def get_subject_image_category_from_wikidata_id(wikidata_id):
    # Connect to Wikidata
    site = pywikibot.Site("wikidata", "wikidata")
    commons_site = pywikibot.Site("commons", "commons")
    repo = site.data_repository()
    
    # Access the Wikidata item using the provided ID
    item = pywikibot.ItemPage(repo, wikidata_id)
    
    # If the item doesn't exist, return None
    if not item.exists():
        print(f"Item {wikidata_id} does not exist!")
        return None
        
    # Try to fetch the value of the property P1472 (Commons Creator page)
    claims = item.get().get('claims')
    
    if 'P373' in claims:
        commons_category_claim = claims['P373'][0]
        commons_category = commons_category_claim.getTarget()
        photo_category = pywikibot.Category(commons_site, commons_category)
        
        # Check if the category exists
        if photo_category.exists():   
            return photo_category.title()
    return None


def get_creator_image_category_from_wikidata_id(wikidata_id):
    # Connect to Wikidata
    site = pywikibot.Site("wikidata", "wikidata")
    commons_site = pywikibot.Site("commons", "commons")
    repo = site.data_repository()
    
    # Access the Wikidata item using the provided ID
    item = pywikibot.ItemPage(repo, wikidata_id)
    
    # If the item doesn't exist, return None
    if not item.exists():
        print(f"Item {wikidata_id} does not exist!")
        return None
        
    # Try to fetch the value of the property P1472 (Commons Creator page)
    claims = item.get().get('claims')
    
    if 'P373' in claims:
        commons_category_claim = claims['P373'][0]
        commons_category = commons_category_claim.getTarget()
        photo_category_name = f"Category:Photographs by {commons_category}"
        photo_category = pywikibot.Category(commons_site, photo_category_name)
        
        # Check if the category exists
        if photo_category.exists():   
            return photo_category.title()
        else:
            print(f'{photo_category.title} is missing')
            exit(1)
#            return None
    else:
         print(f'{wikidata_id}.P373 value is missing')
         exit(1)
#        return None

def get_subject_actors_wikidata_ids(subjectActors):
    ret=[]
    for subjectActor in subjectActors:
        if subjectActor in subjectActorsCache:
            ret.append(subjectActorsCache[subjectActor])
        else:
            print("Error: Unknown actor. Add actor to https://commons.wikimedia.org/wiki/User:FinnaUploadBot/data/subjectActors")
            print(subjectActor)
            exit(1)
    return ret

def parse_cache_page(page_title):
    page = pywikibot.Page(site, page_title)
    cache = parse_name_and_q_item(page.text)
    return cache


pywikibot.config.socket_timeout = 120
site = pywikibot.Site("commons", "commons")  # for Wikimedia Commons
site.login()


nonPresenterAuthorsCache =parse_cache_page('User:FinnaUploadBot/data/nonPresenterAuthors')
institutionsCache=parse_cache_page('User:FinnaUploadBot/data/institutions')
collectionsCache=parse_cache_page('User:FinnaUploadBot/data/collections')
subjectActorsCache=parse_cache_page('User:FinnaUploadBot/data/subjectActors')


