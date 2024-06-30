from django.apps import AppConfig


class MyAppConfig(AppConfig):

    name = 'finnauploader'
    verbose_name = "My Application"

    def ready(self):
        print("apps.py ready()")
        from images.models_mappingcache import NonPresenterAuthorsCache, \
            CollectionsCache, \
            InstitutionsCache, \
            SubjectActorsCache, \
            SubjectPlacesCache

        NonPresenterAuthorsCache.objects.update()
        CollectionsCache.objects.update()
        InstitutionsCache.objects.update()
        SubjectActorsCache.objects.update()
        SubjectPlacesCache.objects.update()
