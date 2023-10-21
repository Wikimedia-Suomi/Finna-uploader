import pywikibot
import json

site = pywikibot.Site('commons', 'commons')
site.login()

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

    # Load file from url
    file_page.upload(source_file_url, comment=comment, asynchronous=True)

    return file_page
