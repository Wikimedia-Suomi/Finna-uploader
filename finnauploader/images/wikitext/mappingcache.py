# mappingcache: only contains mappings from finna-strings to wikidata-qcodes

import re

class MappingCache:
    def __init__(self):
        self.nonPresenterAuthorsCache = None
        self.institutionsCache = None
        self.collectionsCache = None
        self.subjectActorsCache = None
        self.subjectPlacesCache = None

    def parse_name_and_q_item(self, text):
        pattern = r'\*\s(.*?)\s:\s\{\{Q\|(Q\d+)\}\}'
        matches = re.findall(pattern, text)

        # Extracted names and Q-items
        parsed_data = {}
        for name, q_item in matches:
            name = name.strip()
            # if something is wrong, skip it
            if (name.find("http:") >= 0 or name.find("https:") >= 0):
                continue
            if (name.find("//") >= 0):
                continue
            if (q_item.find(':') >= 0):
                continue
            if (q_item.find('^') >= 0):
                continue
            parsed_data[name] = q_item
        return parsed_data

    def parse_cache_page(self, pywikibot, site, page_title):
        print(page_title)
        page = pywikibot.Page(site, page_title)
        cache = self.parse_name_and_q_item(page.text)
        for n in range(2,5):
            page =  pywikibot.Page(site, f'{page_title}_{n}')
            if page.exists():
                sub = self.parse_name_and_q_item(page.text)
                for key, value in sub.items():
                    cache[key] = value
        return cache
    
    def parse_cache(self, pywikibot, site):
        # TODO keep timestamp or other check if list changes:
        # we should refresh/reload if there is a change without need to restart
        # since that happens very often
        self.nonPresenterAuthorsCache = self.parse_cache_page(pywikibot, site, 'User:FinnaUploadBot/data/nonPresenterAuthors') # noqa
        self.institutionsCache = self.parse_cache_page(pywikibot, site, 'User:FinnaUploadBot/data/institutions')
        self.collectionsCache = self.parse_cache_page(pywikibot, site, 'User:FinnaUploadBot/data/collections')
        self.subjectActorsCache = self.parse_cache_page(pywikibot, site, 'User:FinnaUploadBot/data/subjectActors')
        
        # may have very long strings and not used currently
        self.subjectPlacesCache = self.parse_cache_page(pywikibot, site, 'User:FinnaUploadBot/data/subjectPlaces')

# main()
# wikidata_helpers.py has loading and creates instance, no need to do that here
#print("Loading mappings from name to qcode")

