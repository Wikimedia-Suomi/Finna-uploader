import pywikibot
from pywikibot.exceptions import NoPageError
import json
import re
from datetime import datetime

site = pywikibot.Site('commons', 'commons')
site.login()

dtstart = datetime.now()


# Edit Wikimedia Commons mediaitem using wbeditentity
def edit_commons_mediaitem(page, data):
    # Reload file_page to be sure that we have updated page_id

    file_page = pywikibot.FilePage(site, page.title())
    media_identifier = 'M' + str(file_page.pageid)
    print(media_identifier)

    csrf_token = site.tokens['csrf']
    payload = {
        'action': 'wbeditentity',
        'format': u'json',
        'id': media_identifier,
        'data':  json.dumps(data),
        'token': csrf_token,
        'bot': True,  # in case you're using a bot account (which you should)
    }
    request = site.simple_request(**payload)
    ret = request.submit()
    return ret


def upload_file_to_commons(source_file_url, file_name, wikitext, comment):
    commons_file_name = "File:" + file_name
    file_page = pywikibot.FilePage(site, commons_file_name)
    file_page.text = wikitext

    # Check if the page exists
    if file_page.exists():
        print(f"The file {commons_file_name} exists.")
        exit()

    # Check if the page exists
    if site.userinfo['messages']:
        #talk_page = site.user.getUserTalkPage()
        user = pywikibot.User(site, site.username())
        talk_page = user.getUserTalkPage()
        latestdt = talk_page.latest_revision.timestamp
        if (latestdt > dtstart):
            page_name = talk_page.title()
            msg = f'Warning: You have received a {page_name} message. Exiting.'
            print(msg)
            exit()

    # Load file from url
    file_page.upload(source_file_url, comment=comment, asynchronous=True)

    return file_page

def get_comment_text(finna_image):
    authors = list(finna_image.non_presenter_authors
                              .filter(role='kuvaaja')
                              .values_list('name', flat=True))

    ret = "Uploading \'" + finna_image.short_title + "\'"
    ret = ret + " by \'" + "; ".join(authors) + "\'"   
            
    if "CC BY 4.0" in finna_image.image_right.copyright:
        copyrighttemplate = "CC-BY-4.0"
    else:
        print("Copyright error")
        print(finna_image.image_right.copyright)
        exit(1)
                    
    ret = f'{ret} with licence {copyrighttemplate}'
    ret = f'{ret} from {finna_image.url}'
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
        title = url.split('/')[-1]  # This assumes the title is the last segment of the URL
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

