from django.apps import AppConfig

# this is defined in __init__.py, change it if you rename this
class MyAppConfig(AppConfig):

    name = 'finnauploader'
    verbose_name = "My Application"

    # this is called when "registry" has been initialized and may called more than once?
    # also called once on each command.
    def ready(self):
        print("apps.py ready()")
        try:
            from images.models_mappingcache import NonPresenterAuthorsCache, \
                CollectionsCache, \
                InstitutionsCache, \
                SubjectActorsCache, \
                SubjectPlacesCache

#        NonPresenterAuthorsCache.objects.clear()
            NonPresenterAuthorsCache.objects.update()

#        CollectionsCache.objects.clear()
            CollectionsCache.objects.update()

#        InstitutionsCache.objects.clear()
            InstitutionsCache.objects.update()

#        SubjectActorsCache.objects.clear()
            SubjectActorsCache.objects.update()

#        SubjectPlacesCache.objects.clear()
            SubjectPlacesCache.objects.update()
        except:
            pass

