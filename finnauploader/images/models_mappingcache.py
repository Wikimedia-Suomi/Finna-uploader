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
        print("Updating cache for:", page_title)

        site = pywikibot.Site("commons")

        # get latest rev id in database
        defaults = {'rev_id': 0}
        cache = WikitextCache.objects
        obj, created = cache.get_or_create(page_title=page_title,
                                           defaults=defaults)

        # Get latest revid of wiki pages
        rev_id = self._get_latest_revision_id(site, page_title)

        # Test if there is newer revisions in wiki
        update = int(obj.rev_id) < rev_id

        # Update cache if needed:
        # commons page revision has changed or local cache is being initialized
        if created or update:
            print(f'Updating {page_title}')
            self._update_cache(site, page_title, rev_id, obj)

    def _get_latest_revision_id(self, site, page_title):
        rev_id = 0
        for n in range(1, 5):
            if n == 1:
                new_page_title = page_title
            else:
                new_page_title = f'{page_title}_{n}'
            page = pywikibot.Page(site, new_page_title)
            if page.exists() and page.latest_revision_id > rev_id:
                rev_id = page.latest_revision_id
        print("Page:", page_title, "revision:", rev_id)
        return rev_id

    def _update_cache(self, site, page_title, rev_id, obj):
        print("Saving cache for:", page_title)
        mapping = MappingCache()
        rows = mapping.parse_cache_page(site, page_title)

        # TODO: you shouldn't clear entire cache every time
        self.clear()
        for name in rows:
            wikidata_id = rows[name]
            self.get_or_create(name=name, wikidata_id=wikidata_id)
        obj.rev_id = rev_id
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

