from django.db import models
from images.wikitext.mappingcache import MappingCache
import pywikibot


# Store latest wikipage revids to db
class WikitextCache(models.Model):
    page_title = models.CharField(max_length=255)
    rev_id = models.PositiveIntegerField(unique=True)


# so this instance is shared between different caches
# and it doesn't work correctly to save members
# and they are given via the model instead
class FinnaMappingsCacheManager(models.Manager):

    def clear(self):
        self.all().delete()
        page_title = self.model.page_title
        WikitextCache.objects.filter(page_title=page_title).delete()

    def update(self):
        page_title = self.model.page_title
        print("Checking cache for page:", page_title)

        site = pywikibot.Site("commons")

        # get latest rev id in database
        defaults = {'rev_id': 0}
        cache = WikitextCache.objects
        obj, created = cache.get_or_create(page_title=page_title,
                                           defaults=defaults)

        print("Saving cache for:", page_title)
        mapping = MappingCache()
        mapping.base_page_title = page_title

        mapping.parse_cache_pages(site)
        if (obj.rev_id >= mapping.rev_id):
            print("mapping older or equal revision")
            return

        # TODO: you shouldn't clear entire cache every time
        self.clear()
        for name, wikidata_id in mapping.cache.items():
            #wikidata_id = maprows[name]
            self.get_or_create(name=name, wikidata_id=wikidata_id)
            
        obj.rev_id = mapping.rev_id
        obj.save()
        print("Saved cache for:", page_title)

# this is bizarre way to use abstract classes
class FinnaMappingsCache(models.Model):
    # this is used directly during starting since actual app isn't loaded yet
    # and this is actually shared static instance instead of inherited member
    # -> see the bizarre handling in apps.py
    objects = FinnaMappingsCacheManager()
    #cache = WikitextCache()

    page_title = ''
    name = models.CharField(max_length=255)
    wikidata_id = models.CharField(max_length=32)

    class Meta:
        abstract = True


class NonPresenterAuthorsCache(FinnaMappingsCache):
    page_title = 'User:FinnaUploadBot/data/nonPresenterAuthors'


class CollectionsCache(FinnaMappingsCache):
    page_title = 'User:FinnaUploadBot/data/collections'


class InstitutionsCache(FinnaMappingsCache):
    page_title = 'User:FinnaUploadBot/data/institutions'


class SubjectActorsCache(FinnaMappingsCache):
    page_title = 'User:FinnaUploadBot/data/subjectActors'


class SubjectPlacesCache(FinnaMappingsCache):
    page_title = 'User:FinnaUploadBot/data/subjectPlaces'

