from django.apps import AppConfig


class ImagesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'images'

    def ready(self):
        print("ImagesConfig apps.py ready()")
        try:
            from images.models_mappingcache import NonPresenterAuthorsCache, \
                CollectionsCache, \
                InstitutionsCache, \
                SubjectActorsCache, \
                SubjectPlacesCache

            #NonPresenterAuthorsCache.objects.update()
            NonPresenterAuthorsCache.update()
            CollectionsCache.update()
            InstitutionsCache.update()
            SubjectActorsCache.update()
            SubjectPlacesCache.update()
        except:
            pass

