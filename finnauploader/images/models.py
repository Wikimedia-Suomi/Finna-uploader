from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone

# Create your models here.

# Commons image
class Image(models.Model):
    page_id = models.PositiveIntegerField(unique=True)
    page_title = models.CharField(max_length=200)
    finna_id = models.CharField(max_length=200, null=True, blank=True)
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
    finna_id = models.CharField(max_length=200)

    class Meta:
        unique_together = [['image', 'finna_id']]

class ImageHash(models.Model):
    phash = models.BigIntegerField(null=True)  # To store 64-bit unsigned integer
    dhash = models.BigIntegerField(null=True)  # To store 64-bit unsigned integer
    dhash_vertical = models.BigIntegerField(null=True)  # To store 64-bit unsigned integer
    image = models.ForeignKey(Image, related_name="image_hashes", on_delete=models.CASCADE)
    
    class Meta:
        unique_together = [['phash', 'image'], ['dhash', 'image'], ['dhash_vertical', 'image']]

class ImageHashURL(models.Model):
    url = models.URLField(max_length=500)
    image_hash = models.ForeignKey(ImageHash, related_name="image_urls", on_delete=models.CASCADE)
    width = models.PositiveIntegerField(null=False, default=0)
    height = models.PositiveIntegerField(null=False, default=0)
    thumbnail = models.BooleanField(default=False)
    created = models.DateTimeField(default=timezone.now)

# Updates the Image.confirmed_finna_id_updated_at when confirmed_finna_id is updated

@receiver(pre_save, sender=Image)
def update_timestamp(sender, instance, **kwargs):
    # If the instance exists, means it's not a new record
    if instance.pk:
        old_instance = Image.objects.get(pk=instance.pk)
        if old_instance.finna_id_confirmed != instance.finna_id_confirmed:
            instance.finna_id_confirmed_at = timezone.now()

