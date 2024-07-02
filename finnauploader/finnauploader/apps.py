from django.apps import AppConfig


class MyAppConfig(AppConfig):

    name = 'finnauploader'
    verbose_name = "My Application"

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
