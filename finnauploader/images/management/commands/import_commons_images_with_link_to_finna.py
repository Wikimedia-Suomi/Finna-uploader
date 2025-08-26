from django.core.management.base import BaseCommand
from images.models import Image, ImageURL
import pywikibot
import requests

class Command(BaseCommand):
    help = 'Import Wikimedia Commons images with externallinks to Finna to database'

    def add_urls(self, url, match=None):
        print(url)

        # TODO: refactor so that this will use pywikibot.site.exturlusage()
        # https://doc.wikimedia.org/pywikibot/master/api_ref/pywikibot.site.html#pywikibot.site._generators.GeneratorsMixin.exturlusage

        # Find all pages with url

        base_url = f"https://commons.wikimedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "list": "exturlusage",
            "euquery": url,
            "euprop": "ids|title|url",
            "eunamespace": 6,  # Change this to search in other namespaces
            "eulimit": 500,    # Maximum number of results per request
        }

        S = requests.Session()
        S.headers.update({'User-Agent': 'FinnaUploader 0.2 (https://commons.wikimedia.org/wiki/User:FinnaUploadBot)'}) # noqa
 

        # Load only 500 url per round and iterate until there is no new urls
        while True:
            response = S.get(base_url, params=params)
            data = response.json()

            if "query" in data:
                for link in data["query"]["exturlusage"]:
                    if match and match not in link['url']:
                        continue

                    # Do actual updating
                    print(link)
                    image, created = Image.objects.get_or_create(page_id=link['pageid'], defaults={"page_title": link['title']})
                    image_url, image_created = ImageURL.objects.get_or_create(image=image, url=link['url'])
                    
            if "continue" in data:
                params["eucontinue"] = data["continue"]["eucontinue"]
            else:
                break

#    def add_arguments(self, parser):
#        parser.add_argument('url', type=str)

    def handle(self, *args, **kwargs):
        self.add_urls('finna.fi')
        self.add_urls('kuvakokoelmat.fi')
        self.add_urls('kokoelmat.fng.fi')
        self.add_urls('europeana.eu', '2021009')

        self.stdout.write(self.style.SUCCESS(f'Pages added successfully!'))
