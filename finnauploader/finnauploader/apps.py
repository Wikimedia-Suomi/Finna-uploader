from django.apps import AppConfig

# this is defined in __init__.py, change it if you rename this
class MyAppConfig(AppConfig):

    name = 'finnauploader'
    verbose_name = "My Application"

    # this is called when "registry" has been initialized and may called more than once?
    # also called once on each command.
    def ready(self):
        print("MyAppConfig ready()")
        
        # this following bizarre thing is because actual application has not been loaded yet?
        # we get errors otherwise
        try:
            from images.models_mappingcache import NonPresenterAuthorsCache, \
                CollectionsCache, \
                InstitutionsCache, \
                SubjectActorsCache, \
                SubjectPlacesCache

            NonPresenterAuthorsCache.objects.update()
            NonPresenterAuthorsCache.objects.update()
            CollectionsCache.objects.update()
            InstitutionsCache.objects.update()
            SubjectActorsCache.objects.update()
            SubjectPlacesCache.objects.update()
            
            #NonPresenterAuthorsCache.updateCache()
            #CollectionsCache.updateCache()
            #InstitutionsCache.updateCache()
            #SubjectActorsCache.updateCache()
            #SubjectPlacesCache.updateCache()
        except:
            pass
