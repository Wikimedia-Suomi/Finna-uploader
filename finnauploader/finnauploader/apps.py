from django.apps import AppConfig

# this is defined in __init__.py, change it if you rename this
class MyAppConfig(AppConfig):

    name = 'finnauploader'
    verbose_name = "My Application"

    # this is called when "registry" has been initialized and may called more than once?
    # also called once on each command.
    def ready(self):
        print("MyAppConfig ready()")
