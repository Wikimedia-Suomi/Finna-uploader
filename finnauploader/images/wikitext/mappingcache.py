# mappingcache: only contains mappings from finna-strings to wikidata-qcodes

import re
import pywikibot


class MappingCache:

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

    def parse_cache_page(self, site, page_title):
        print("Loading page:", page_title)
        page = pywikibot.Page(site, page_title)
        cache = self.parse_name_and_q_item(page.text)
        for n in range(2, 5):
            page = pywikibot.Page(site, f'{page_title}_{n}')
            if page.exists():
                sub = self.parse_name_and_q_item(page.text)
                for key, value in sub.items():
                    cache[key] = value
        return cache
