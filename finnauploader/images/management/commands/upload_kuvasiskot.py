from django.core.management.base import BaseCommand
from images.models import Image, ImageURL, FinnaImageHash, FinnaNonPresenterAuthor, FinnaImage
import pywikibot
from pywikibot.data import sparql
import requests
from django.db.models import Count
import time
from images.finna import do_finna_search
import json
import mwparserfromhell
import re
from datetime import datetime
from images.sdc_helpers import create_P7482_source_of_file, create_P275_licence, create_P6216_copyright_state, create_P9478_finna_id, create_P170_author, create_P195_collection, create_P571_timestamp, wbEditEntity
from images.wikitext.creator import get_institution_name, get_institution_wikidata_id, get_institution_template_from_wikidata_id, get_author_name, get_author_wikidata_id, get_creator_template_from_wikidata_id
from images.wikitext.photographer import create_photographer_template
from images.wikitext.categories import create_categories
from images.wikitext.timestamps import parse_timestamp

def get_sdc_json(r):
    url='https://www.finna.fi/Record/' + r['id']
    operator='Q420747' # National library
    publisher='Q3029524' # Finnish Heritage Agency

    labels={}
    labels['fi']={'language':'fi', 'value': r['title'] }

    claims=[]
    claim=create_P7482_source_of_file(url, operator, publisher)
    claims.append(claim)

    claim = create_P275_licence(value=r['copyright'])
    claims.append(claim)

    claim = create_P6216_copyright_state(value=r['copyright'])
    claims.append(claim)

    claim = create_P9478_finna_id(r['id'])
    claims.append(claim)

    claim = create_P170_author(r['creator_wikidata_id'], 'Q33231') # Kuvasiskot, kuvaaja
    claims.append(claim)

    for collection in r['collections']:
        claim = create_P195_collection(collection, r['identifierString'])
        claims.append(claim)

    parsed_timestamp,precision=parse_timestamp(r['date'])
    if parsed_timestamp:
        timestamp=datetime.strptime(parsed_timestamp, "+%Y-%m-%dT%H:%M:%SZ")
        claim = create_P571_timestamp(timestamp,precision)
        claims.append(claim)

    json_claims=[]
    for claim in claims:
        claim=claim.toJSON()
        json_claims.append(claim)

    ret={
        'labels':labels,
        'claims':json_claims
    }
    return ret


def upload_file_to_commons(source_file_url, file_name, wikitext, comment):
    site = pywikibot.Site('commons', 'commons')  # The site we want to run our bot on
    site.login()

    commons_file_name = "File:" + file_name
    file_page = pywikibot.FilePage(site, commons_file_name)
    file_page.text = wikitext
        
    # Check if the page exists
    if file_page.exists():
        print(f"The file {commons_file_name} exists.")
        exit()
        
    # Load file from url
    file_page.upload(source_file_url, comment=comment,asynchronous=True)
    
    return file_page


def get_comment_text(r):
                     
    ret = "Uploading \'" + r['shortTitle'] +"\'"
    ret = ret + " by \'" + r['creator_name'] +"\'"
                            
    if "CC BY 4.0" in r['copyright']:
        copyrighttemplate="CC-BY-4.0"
    else:
        print("Copyright error")
        print(r['copyright'])
        exit(1)
                             
    ret = ret + " with licence " + copyrighttemplate
    ret = ret + " from " + r['source']
    return ret


# Filter out duplicate placenames
def get_subject_place(subjectPlaces):
    parts = [part.strip() for part in subjectPlaces.split("; ")]

    # Sort the parts by length in descending order
    parts.sort(key=len, reverse=True)
    # Iterate over the parts and check for each part if it's included in any of the parts that come after it
    final_parts = []
    for i in range(len(parts)):
        if not parts[i] in "; ".join(final_parts):
            final_parts.append(parts[i])
    return "; ".join(final_parts)
                

def finna_exists(id):  
    url='https://imagehash.toolforge.org/finnasearch?finna_id=' + str(id)
    print(url)
    response = requests.get(url)
    response.raise_for_status()  # Raise an exception for HTTP errors
    data = response.json()
    print(data)
    if len(data):
        return True
    else:
        return False

def get_existing_finna_ids_from_sparql():
    print("Loading existing photo Finna ids using SPARQL")
    # Define the SPARQL query
    query = "SELECT ?item ?finna_id WHERE { ?item wdt:P9478 ?finna_id }"
              
    # Set up the SPARQL endpoint and entity URL
    # Note: https://commons-query.wikimedia.org requires user to be logged in
                     
    entity_url = 'https://commons.wikimedia.org/entity/'
    endpoint = 'https://commons-query.wikimedia.org/sparql'
                            
    # Create a SparqlQuery object
    query_object = sparql.SparqlQuery(endpoint= endpoint, entity_url= entity_url)
                                    
    # Execute the SPARQL query and retrieve the data
    data = query_object.select(query, full_data=True)
    if data == None:
        print("SPARQL Failed. login BUG?")
        exit(1)
    return data

# get edit summaries of last 5000 edits for checking which files were already uploaded
def get_upload_summary():
    site = pywikibot.Site('commons', 'commons')  # The site we want to run our bot on
    site.login()
    user = site.user()       # The user whose edits we want to check
    user = pywikibot.User(site, str(user))             
    contribs = user.contributions(total=5000)  # Get the user's last 1000 contributions
            
    uploadsummary=''
    for contrib in contribs:
        uploadsummary+=str(contrib) +"\n"
                            
    user = pywikibot.User(site, 'Zache')       # The user whose edits we want to check
    contribs = user.contributions(total=5000)  # Get the user's last 1000 contributions

    for contrib in contribs:
        uploadsummary+=str(contrib) +"\n"

    user = pywikibot.User(site, 'FinnaUploadBot')       # The user whose edits we want to check
    contribs = user.contributions(total=5000)  # Get the user's last 1000 contributions
                                
    for contrib in contribs:
        uploadsummary+=str(contrib) +"\n"
                                  
    return uploadsummary


class Command(BaseCommand):
    help = 'Upload kuvasiskot images'

    def process_finna_record(self, record):        
        site = pywikibot.Site('commons', 'commons')  # The site we want to run our bot on
        site.login()

        images=[]
        print(record['id'])
        print(record['title'])
        print(record['summary'])

        r={}
        r['id']=record['id']
        r['title']=record['title']
        r['shortTitle']=record['shortTitle']
        r['copyright']=record['imageRights']['copyright']
        r['thumbnail']="https://finna.fi" + record['imagesExtended'][0]['urls']['small']
        r['image_url']= record['imagesExtended'][0]['highResolution']['original'][0]['url']
        r['image_format']= record['imagesExtended'][0]['highResolution']['original'][0]['format']
        r['collections']=record['collections']
        r['institutions']=record['institutions']
        r['institution_name']=get_institution_name(r['institutions'])
        r['institution_wikidata_id']=get_institution_wikidata_id(r['institution_name'])
        r['institution_template']=get_institution_template_from_wikidata_id(r['institution_wikidata_id'])
        r['identifierString']=record['identifierString']
        r['subjectPlaces']=get_subject_place("; ".join(record['subjectPlaces']))
        r['subjectActors']="; ".join(record['subjectActors'])
        if not r['subjectActors']:
            return

        try:
            r['date']=record['events']['valmistus'][0]['date']
        except:
            r['date']=''
        r['source']='https://finna.fi/Record/' + r['id']
        r['subjects']=record['subjects']
        r['measurements']=record['measurements']
    
        # Check copyright
        if r['copyright'] == "CC BY 4.0":
            r['copyright_template']="{{CC-BY-4.0}}\n{{FinnaReview}}"
            r['copyright_description']=record['imagesExtended'][0]['rights']['description'][0]
        else:
            print("Unknown copyright: " + r['copyright'])
            exit(1)

        # Check format
        if r['image_format'] == 'tif':
           # Filename format is "tohtori,_varatuomari_Reino_Erma_(647F28).tif"
#           r['file_name'] = r['shortTitle'].replace(" ", "_") + '_(' + r['id'][-6:] +  ').tif'
           r['file_name'] = r['shortTitle'].replace(" ", "_") + '_(' + r['identifierString'].replace(":", "-") +  ').tif'
           r['file_name'] = r['file_name'].replace(":", "_")
        else:
            print("Unknown format: " + r['image_format'])
            exit(1)
    
        # Skip image already exits in Wikimedia Commons
        #if check_imagehash(r['thumbnail']):
        #    print("Skipping (already exists based on imagehash) : " + r['id'])
        #    continue

        r['creator_name']=get_author_name(record['nonPresenterAuthors'])    
        r['creator_wikidata_id']=get_author_wikidata_id(r['creator_name'])
        r['creator_template']=get_creator_template_from_wikidata_id(r['creator_wikidata_id'])
        # titles and descriptions wrapped in language template
        r['template_titles']=['{{fi|' + r['title'] + '}}']
        r['template_descriptions']={}

#        print(json.dumps(r, indent=3))
#        print(record)

        wikitext_parts=[]
        wikitext_parts.append("== {{int:filedesc}} ==")
        wikitext_parts.append(create_photographer_template(r) + '\n')
        wikitext_parts.append("== {{int:license-header}} ==")
        wikitext_parts.append(r['copyright_template'])
        wikitext_parts.append(create_categories(r))        
        wikitext = "\n".join(wikitext_parts)

        structured_data=get_sdc_json(r)

        comment=get_comment_text(r)
        pywikibot.info('')
        pywikibot.info(wikitext)
        pywikibot.info('')
        pywikibot.info(comment)
        print(r['image_url'])
        question='Do you want to upload this file?'

        choice = pywikibot.input_choice(
            question,
            [('Yes', 'y'), ('No', 'N')],
            default='N',
            automatic_quit=False
        )
        print(r['file_name'])
        if choice == 'y':
            page=upload_file_to_commons(r['image_url'], r['file_name'], wikitext, comment)
            wbEditEntity(site, page, structured_data)

    def handle(self, *args, **kwargs):
        
        print("Loading 5000 most recent edit summaries for skipping already uploaded photos")
        uploadsummary=get_upload_summary()
        sparql_finna_ids=str(get_existing_finna_ids_from_sparql())

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

                    print(".")
                    # Not photo
                    if not 'imagesExtended' in record:
                        contineu
    
                    # Check if image is already uploaded
                    if record['id'] in sparql_finna_ids:
                        print("Skipping 1: " + record['id'] + " already uploaded based on sparql")
                        continue
        
                    if record['id'] in uploadsummary:
                        print("Skipping 2: " + record['id'] + " already uploaded based on upload summaries")
                        continue  
        
                    if finna_exists(record['id']):
                        print("Skipping 3: " + record['id'] + " already uploaded based on imagehash")
                        continue
                    self.process_finna_record(record)


             else:
                 break



