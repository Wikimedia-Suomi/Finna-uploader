import pywikibot
from pywikibot.exceptions import NoPageError
import json
import re
from datetime import datetime
from pywikibot.data.sparql import SparqlQuery


# should do this here instead of in wikidata_helpers.py ?
pywikibot.config.socket_timeout = 120

dtstart = datetime.now()


def are_there_messages_for_bot_in_commons():

    commonssite = pywikibot.Site('commons', 'commons')
    commonssite.login()
    
    # Check if the page exists
    if commonssite.userinfo['messages']:
        # talk_page = commonssite.user.getUserTalkPage()
        user = pywikibot.User(commonssite, commonssite.username())
        talk_page = user.getUserTalkPage()
        latestdt = talk_page.latest_revision.timestamp
        if (latestdt > dtstart):
            page_name = talk_page.title()
            msg = f'Warning: You have received a {page_name} message. Exiting.'
            print(msg)
            
            # abort upload
            exit()
            return True
    return False


# Edit Wikimedia Commons mediaitem using wbeditentity
def edit_commons_mediaitem(commonssite, page_title, data):
    
    # Reload file_page to be sure that we have updated page_id

    file_page = pywikibot.FilePage(commonssite, page_title)
    media_identifier = 'M' + str(file_page.pageid) # what is in pageid on error?
    print("media identifier: ", media_identifier)

    csrf_token = commonssite.tokens['csrf']
    payload = {
        'action': 'wbeditentity',
        'format': u'json',
        'id': media_identifier,
        'data':  json.dumps(data),
        'token': csrf_token,
        'bot': True,  # in case you're using a bot account (which you should)
    }
    request = commonssite.simple_request(**payload)
    ret = request.submit()
    return ret


def is_qid(page_title):
    return bool(re.match(r'^Q\d+$', page_title))


def parse_qid_from_wikidata_url(url):
    ret = None

    if 'https://wikidata.org/wiki/Q' in url:
        ret = url.replace('https://wikidata.org/wiki/', '')
    elif 'http://wikidata.org/wiki/Q' in url:
        ret = url.replace('http://wikidata.org/wiki/', '')
    elif '//wikidata.org/wiki/Q' in url:
        ret = url.replace('//wikidata.org/wiki/', '')
    return ret


def parse_qid_from_commons_category(url):
    ret = None

    if '//' not in url and 'category:' in url.lower():
        try:
            site = pywikibot.Site('commons')
            page = pywikibot.Page(site, url)
            data_item = page.data_item()
            # Get the associated DataItem (Wikidata item) for the page
            ret = data_item.id
        except:
            pass
    return ret


def parse_wikidata_id_from_url(url):
    try:
        # Create a Site object from the URL
        site = pywikibot.Site(url=url)

        # Extract the page title from the URL and get the Page object
        # This assumes the title is the last segment of the URL
        title = url.split('/')[-1]
        page = pywikibot.Page(site, title)
        data_item = page.data_item()

        # Get the associated DataItem (Wikidata item) for the page
        return data_item.id
    except NoPageError:
        return None
    except IndexError:
        return False
    return None


def get_wikidata_id_from_url(url):
    if is_qid(url):
        return url

    ret = parse_qid_from_commons_category(url)
    if ret:
        return ret

    ret = parse_qid_from_wikidata_url(url)
    if ret:
        return ret

    ret = parse_wikidata_id_from_url(url)
    if ret:
        return ret

    return None


def test_if_finna_id_exists_in_commons(finna_id, slow=False):
    query = """
SELECT DISTINCT ?media ?finna_id ?phash ?dhash WHERE {
    ?media wdt:P9478 __finna_id__ .
    OPTIONAL { ?media wdt:P9310 ?phash }
    OPTIONAL { ?media wdt:P12563 ?dhash }
} LIMIT 3
"""

    query = query.replace('__finna_id__', f'"{finna_id}"')
    endpoint = 'https://commons-query.wikimedia.org/sparql'
    entity_url = 'https://commons.wikimedia.org/entity/'
    sparql = SparqlQuery(endpoint=endpoint, entity_url=entity_url)
    data = sparql.select(query)
    return data
