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
from images.sdc_helpers import create_P7482_source_of_file, create_P275_licence, create_P6216_copyright_state, create_P9478_finna_id, create_P170_author, create_P195_collection, create_P571_timestamp

pywikibot.config.socket_timeout = 120
site = pywikibot.Site("commons", "commons")  # for Wikimedia Commons
site.login()


def parse_name_and_q_item(text):
    pattern = r'\*\s(.*?)\s:\s\{\{Q\|(Q\d+)\}\}'
    matches = re.findall(pattern, text)
    
    # Extracted names and Q-items
    parsed_data = {}
    for name, q_item in matches:
        parsed_data[name] = q_item
    return parsed_data


authors_page_title='User:FinnaUploadBot/data/nonPresenterAuthors'
page = pywikibot.Page(site, authors_page_title)
nonPresenterAuthorsCache = parse_name_and_q_item(page.text) 

institutions_page_title='User:FinnaUploadBot/data/institutions'
page = pywikibot.Page(site, institutions_page_title)
institutionsCache = parse_name_and_q_item(page.text) 

def get_sdc_json(r):
    url='https://www.finna.fi/Record/' + r['id']
    operator='Q420747' # National library
    publisher='Q3029524' # Finnish Heritage Agency
    parsed_timestamp,precision=parse_timestamp(r['date'])
    timestamp=datetime.strptime(parsed_timestamp, "+%Y-%m-%dT%H:%M:%SZ")

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

def wbEditEntity(site, page, data):
    # Reload file_page to be sure that we have updated page_id
                    
    file_page = pywikibot.FilePage(site, page.title())
    media_identifier = 'M' + str(file_page.pageid)
    print(media_identifier)
                
    csrf_token = site.tokens['csrf']
    payload = {
       'action' : 'wbeditentity',
       'format' : u'json',
       'id' : media_identifier,
       'data' :  json.dumps(data),
       'token' : csrf_token,
       'bot' : True, # in case you're using a bot account (which you should)
    }
    print(payload)
    request = site.simple_request(**payload)
    ret=request.submit()  

def upload_file_to_commons(source_file_url, file_name, wikitext, comment):
    commons_file_name = "File:" + file_name
    file_page = pywikibot.FilePage(site, commons_file_name)
    file_page.text = wikitext
        
    # Check if the page exists
    if file_page.exists():
        print(f"The file {commons_file_name} exists.")
        exit()
        
    # Load file from url
#    response = requests.get(source_file_url,  timeout=30)
    
    # Create a temporary file and save the downloaded file into this temp file
#    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
#        temp_file.write(response.content)
#        temp_file_path = temp_file.name
    
#    file_page.upload(temp_file_path, comment=comment,asynchronous=True)
    file_page.upload(source_file_url, comment=comment,asynchronous=True)
    
    # Delete the temporary file
#    os.unlink(temp_file_path)  
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


def parse_timestamp(datestr):
   # str = "valmistusaika: 22.06.2015"
   m = re.match("valmistusaika:? (\d\d)\.(\d\d)\.(\d\d\d\d)", datestr)
   if m!=None:
      year=m.group(3)     
      month=m.group(2)
      day=m.group(1)
      timestamp="+" + year +"-" + month +"-" + day +"T00:00:00Z"
      precision=11
      return timestamp, precision
    
   m = re.match("valmistusaika:? (\d\d\d\d)", datestr)
   if m!=None:
      year=m.group(1)
      timestamp="+" + year +"-01-01T00:00:00Z"
      precision=9
      return timestamp, precision
      
   print(datestr)   
   exit("Parse_timestamp failed")


def parse_timestamp_string(datestr):
   if not datestr:
       return ''

   m = re.match("valmistusaika:? (\d\d)\.(\d\d)\.(\d\d\d\d)$", datestr.strip())
   if m!=None:
      year=m.group(3)
      month=m.group(2)
      day=m.group(1)
      timestamp=year +"-" + month +"-" + day
      return timestamp
        
   m = re.match("valmistusaika:? (\d\d\d\d)$", datestr.strip())
   if m!=None:              
      year=m.group(1)
      return year
        
   print(datestr)
   exit("Parse_timestamp failed") 

def language_template_wrap(lang, text):
    if text:
        return '{{' + lang + '|' + text + '}}'
    else:
        return ''

def create_categories(r):
    # Create a new WikiCode object
    wikicode = mwparserfromhell.parse("")
    
    # Create the categories
    categories = set()

    creator_category=get_creator_image_category_from_wikidata_id(r['creator_wikidata_id'])
    creator_category=creator_category.replace('Category:', '')
    categories.add(creator_category)
        
    subject_categories = {
        'muotokuvat':'Portrait photographs',
        'henkilökuvat':'Portrait photographs',
        'professorit':'Professors from Finland',
        'miesten puvut':'Men wearing suits in Finland'
    }
    
    for subject_category in subject_categories.keys():
        if subject_category in str(r['subjects']):
            categories.add(subject_categories[subject_category])

    
    if 'year' in r:
        if 'Category:Portrait photographs' in categories:
            categories.add('People of Finland in ' + r['year'])
        else:
            categories.add(r['year'] + ' in Finland')

    categories.add('Files uploaded by FinnaUploadBot')
    
    for category in categories:
        # Create the Wikilink
        wikilink = mwparserfromhell.nodes.Wikilink(title='Category:' + category)
                
        # Add the Wikilink to the WikiCode object
        wikicode.append(wikilink)    
    
        
    flatten_wikicode=str(wikicode).replace('[[Category:', '\n[[Category:')
                                
    # return the wikitext 
    return flatten_wikicode

def create_photographer_template(r):
    # Create a new WikiCode object
    wikicode = mwparserfromhell.parse("")
 
    # Create the template
    template = mwparserfromhell.nodes.Template(name='Photograph')

    # Add the parameters to the template
    template.add('photographer', r['creator_template'])
    template.add('title', '\n'.join(r['template_titles']))
    template.add('description', language_template_wrap('fi', '\n'.join(r['template_descriptions'])))
    template.add('depicted people', language_template_wrap('fi', r['subjectActors']))
    template.add('depicted place', language_template_wrap('fi', r['subjectPlaces']))
    template.add('date', parse_timestamp_string(r['date']))
    template.add('medium', '')
    template.add('dimensions', "\n".join(r['measurements']))
    template.add('institution', r['institution_template'])   
    template.add('department', language_template_wrap('fi', "; ".join(r['collections'])))
    template.add('references', '')
    template.add('object history', '')
    template.add('exhibition history', '')
    template.add('credit line', '')
    template.add('inscriptions', '')
    template.add('notes', '')
    template.add('accession number', r['identifierString'])
    template.add('source', r['source'])
    template.add('permission',  language_template_wrap('fi', "\n".join([r['copyright'], r['copyright_description']])))
    template.add('other_versions', '')
    template.add('wikidata', '')
    template.add('camera coord', '')

    # Add the template to the WikiCode object
    wikicode.append(template)
    flatten_wikitext=str(wikicode)
    
    # Add newlines before parameter name
    params = ['photographer', 'title', 'description', 'depicted people', 'depicted place', 'date', 'medium', 'dimensions',
              'institution', 'department', 'references', 'object history', 'exhibition history', 'credit line', 'inscriptions',
              'notes', 'accession number', 'source', 'permission', 'other_versions', 'wikidata', 'camera coord']
    
    for param in params:
        flatten_wikitext=flatten_wikitext.replace('|' + param +'=', '\n|' +param +' = ')
    
    # return the wikitext
    return flatten_wikitext   

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




# Get institution template
#def get_institution(institutions):
#    for institution in institutions: 
#        if institution['value'] == "Museovirasto":
#            ret="{{institution:Museovirasto}}"
#        else: 
#            print("Unknown institution: " + str(institutions))
#            exit(1)
#    return ret
                

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
def get_upload_summary(username):
    site = pywikibot.Site('commons', 'commons')  # The site we want to run our bot on
    user = pywikibot.User(site, username)       # The user whose edits we want to check
                 
    contribs = user.contributions(total=5000)  # Get the user's last 1000 contributions
            
    uploadsummary=''
    for contrib in contribs:
        uploadsummary+=str(contrib) +"\n"
                            
    user = pywikibot.User(site, 'Zache')       # The user whose edits we want to check
    contribs = user.contributions(total=5000)  # Get the user's last 1000 contributions
                                
    for contrib in contribs:
        uploadsummary+=str(contrib) +"\n"
                                  
    return uploadsummary


class Command(BaseCommand):
    help = 'Upload kuvasiskot images'

    def process_finna_record(self, record):        
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
        uploadsummary=get_upload_summary(site.user())
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



