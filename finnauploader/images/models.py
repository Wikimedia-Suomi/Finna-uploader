from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

# Create your models here.

# Commons image
class Image(models.Model):
    page_id = models.PositiveIntegerField(unique=True)
    page_title = models.CharField(max_length=200)
    finna_id = models.CharField(max_length=200, null=True, blank=True, db_index=True)
    finna_id_confirmed = models.BooleanField(default=False)
    finna_id_confirmed_at = models.DateTimeField(null=True, blank=True)

# Commons external links linked from image
class ImageURL(models.Model):
    image = models.ForeignKey(Image, related_name="urls", on_delete=models.CASCADE)
    url = models.URLField(max_length=500)

    class Meta:
        unique_together = [['image', 'url']]

# Commons external links linked from image
class SdcFinnaID(models.Model):
    image = models.ForeignKey(Image, related_name="sdc_finna_ids", on_delete=models.CASCADE)
    finna_id = models.CharField(max_length=200, db_index=True)

    class Meta:
        unique_together = [['image', 'finna_id']]

class FinnaBuilding(models.Model):
     value = models.CharField(max_length=64)
     translated = models.CharField(max_length=64)

     def __str__(self):
        return self.translated

class FinnaCopyright(models.Model):
     copyright = models.CharField(max_length=32)
     link = models.URLField(max_length=500)
     description = models.TextField()

     def __str__(self):
        return self.copyright

class FinnaNonPresenterAuthor(models.Model):
     name = models.CharField(max_length=64)
     role = models.CharField(max_length=64)

     def __str__(self):
        return self.name

class FinnaSummary(models.Model):
     name = models.CharField(max_length=200)

     def __str__(self):
        return self.name

class FinnaSubject(models.Model):
     name = models.CharField(max_length=200)

     def __str__(self):
        return self.name

class FinnaSubjectPlace(models.Model):
     name = models.CharField(max_length=200)

     def __str__(self):
        return self.name

class FinnaSubjectActor(models.Model):
     name = models.CharField(max_length=200)

     def __str__(self):
        return self.name

class FinnaSubjectDetail(models.Model):
     name = models.CharField(max_length=200)

     def __str__(self):
        return self.name

class FinnaCollection(models.Model):
     name = models.CharField(max_length=200)

     def __str__(self):
        return self.name

class FinnaImage(models.Model):
    finna_id =  models.CharField(max_length=200, null=False, blank=False, db_index=True)
    title = models.CharField(max_length=200)
    year = models.PositiveIntegerField(unique=False, null=True, blank=True)
    number_of_images = models.PositiveIntegerField(unique=False, null=True, blank=True)
    non_presenter_authors = models.ManyToManyField(FinnaNonPresenterAuthor, related_name='non_presenter_authors')
    summary = models.ForeignKey(FinnaSummary, related_name='summary', null=True, on_delete=models.CASCADE)
    subjects = models.ManyToManyField(FinnaSubject, related_name='subjects')
    subject_places = models.ManyToManyField(FinnaSubjectPlace, related_name='subject_places')
    subject_actors = models.ManyToManyField(FinnaSubjectActor, related_name='subject_actors')
    subject_details = models.ManyToManyField(FinnaSubjectDetail, related_name='subject_details')
    collections = models.ManyToManyField(FinnaCollection, related_name='collections')
    buildings = models.ManyToManyField(FinnaBuilding, related_name='buildings')
    copyright = models.ForeignKey(FinnaCopyright, related_name="finna_copyright", on_delete=models.CASCADE)
    identifier_string = models.CharField(max_length=64, null=True, blank=True) # accession number or similar identifier
    short_title = models.CharField(max_length=200, null=True, blank=True)

class FinnaImageHash(models.Model):
    phash = models.BigIntegerField(null=True)  # To store 64-bit unsigned integer
    dhash = models.BigIntegerField(null=True)  # To store 64-bit unsigned integer
    dhash_vertical = models.BigIntegerField(null=True)  # To store 64-bit unsigned integer
    finna_image = models.ForeignKey(FinnaImage, related_name="image_hashes", on_delete=models.CASCADE)

    class Meta:
        unique_together = [['phash', 'finna_image'], ['dhash', 'finna_image'], ['dhash_vertical', 'finna_image']]

class FinnaImageHashURL(models.Model):
    url = models.URLField(max_length=500)
    imagehash = models.ForeignKey(FinnaImageHash, related_name="image_urls", on_delete=models.CASCADE)
    width = models.PositiveIntegerField(null=False, default=0)
    height = models.PositiveIntegerField(null=False, default=0)
    index = models.PositiveIntegerField(null=False, default=0)
    thumbnail = models.BooleanField(default=False)
    created = models.DateTimeField(default=timezone.now)

class ToolforgeImageHashCache(models.Model):
    page_id = models.PositiveIntegerField()
    phash = models.BigIntegerField(null=True, db_index=True)  # To store 64-bit unsigned integer
    dhash = models.BigIntegerField(null=True, db_index=True)  # To store 64-bit unsigned integer

# Updates the Image.confirmed_finna_id_updated_at when confirmed_finna_id is updated

@receiver(pre_save, sender=Image)
def update_timestamp(sender, instance, **kwargs):
    # If the instance exists, means it's not a new record
    if instance.pk:
        old_instance = Image.objects.get(pk=instance.pk)
        if old_instance.finna_id_confirmed != instance.finna_id_confirmed:
            instance.finna_id_confirmed_at = timezone.now()

