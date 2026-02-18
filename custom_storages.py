from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class StaticStorage(S3Boto3Storage):
    location = getattr(settings, "STATICFILES_LOCATION", "static")
    default_acl = None          # ✅ bucket has ACLs disabled
    file_overwrite = True


class MediaStorage(S3Boto3Storage):
    location = getattr(settings, "MEDIAFILES_LOCATION", "media")
    default_acl = None          # ✅ bucket has ACLs disabled
    file_overwrite = False
