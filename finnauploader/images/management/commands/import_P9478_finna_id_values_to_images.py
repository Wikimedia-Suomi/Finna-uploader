from django.core.management.base import BaseCommand
from images.models import Image, SdcFinnaID
from pywikibot.data import sparql
import pywikibot
import requests

class Command(BaseCommand):
    help = 'Import Wikimedia Commons P9478 values to images'


    def get_mediawiki_page_by_page_id(self, site, page_id):
        pages = site.load_pages_from_pageids([page_id])
        for page in pages:
            return page

    def get_existing_finna_ids_from_sparql(self):
        print("Loading existing photo Finna ids using SPARQL")
        # Define the SPARQL query
        query = "SELECT DISTINCT ?item ?finna_id WHERE { ?item wdt:P9478 ?finna_id }"
   
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

    def handle(self, *args, **kwargs):
        site = pywikibot.Site("commons", "commons")  # for Wikimedia Commons
        site.login()

        rows=self.get_existing_finna_ids_from_sparql()
        for row in rows:
            print(row)
            page_id=int(str(row['item']).replace('https://commons.wikimedia.org/entity/M', ''))
            try:
                image = Image.objects.get(page_id=page_id)
            except Image.DoesNotExist:
                page=self.get_mediawiki_page_by_page_id(site, page_id)
                page_title=page.title()
                print(f'Image with page_id={page_id} ({page_title}) does not exist.')
                break

            sdc_finna_id, created = SdcFinnaID.objects.get_or_create(image=image, finna_id=row['finna_id'])
            print(created)

        self.stdout.write(self.style.SUCCESS(f'SDC Finna_ids added successfully!'))
