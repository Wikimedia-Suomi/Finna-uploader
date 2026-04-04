# mappingcache: only contains mappings from finna-strings to wikidata-qcodes

import re
import pywikibot


class MappingCache:

    def __init__(self):
        # TODO: map revision per sub-page
        self.rev_id = 0
        #self.cache = {}

    # perform simple checks that values are usable
    def validate_text(self, text):
        if (text.find("http:") >= 0 or text.find("https:") >= 0):
            return False
        if (text.find('^') >= 0):
            return False
        return True

    def parse_name_and_q_item(self, text):
        pattern = r'\*\s(.*?)\s:\s\{\{Q\|(Q\d+)\}\}'
        matches = re.findall(pattern, text)

        # Extracted names and Q-items
        parsed_data = {}
        for name, q_item in matches:
            name = name.strip()
            # if something is wrong, skip it
            if (self.validate_text(name) is False):
                continue
            if (self.validate_text(q_item) is False):
                continue
            # further checks for q-codes
            if (q_item.find("//") >= 0):
                continue
            if (q_item.find(':') >= 0):
                continue
            parsed_data[name] = q_item
        return parsed_data

    def parse_mapping_from_page(self, page):
        mapping = {}
        if not page.exists():
            return mapping

        print("Parsing mapping from page:", page.title())
        sub = self.parse_name_and_q_item(page.text)
        for key, value in sub.items():
            mapping[key] = value
        return mapping

    def parse_cache_pages(self, site, page_title):
        rev_id = 0

        # avoid clearing if possible
        #self.cache.clear()

        print("Loading mapping pages:", page_title)
        cache = {}
        for n in range(0, 6):
            new_page_title = ""
            if n == 0:
                new_page_title = page_title
            else:
                new_page_title = f'{page_title}_{n}'

            # we need to load the page to get revision so might as well parse it..
            print("Loading page:", new_page_title)
            page = pywikibot.Page(site, new_page_title)
            
            if page.exists() and page.latest_revision_id > rev_id:
                print("Updating from page:", page.title(), "revision:", page.latest_revision_id)
                #rev_id = page.latest_revision_id

                sub = self.parse_to_cache_from_page(page)
                for key, value in sub.items():
                    cache[key] = value
            else:
            #    print("Page:", page.title(), "has revision:", page.latest_revision_id)
                print("Page:", new_page_title, " does not exist or is older")

        self.rev_id = rev_id
        return cache


    def is_cached(self, name):
        try:
            obj = self.objects.get(name=name)
            return True
        except:
            pass
        return False
