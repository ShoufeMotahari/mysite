import boto3
from django.conf import settings
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)

def delete_file(file_path):
    """
    حذف فایل از آروان کلود
    :param file_path: مسیر فایل داخل باکت (مثلاً avatars/test.jpg)
    """
    s3 = boto3.client(
        's3',
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )

    try:
        s3.delete_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=file_path)
        logger.info("فایل %s با موفقیت از آروان حذف شد", file_path)
        return True
    except ClientError as e:
        logger.error("خطا در حذف فایل %s از آروان: %s", file_path, str(e))
        return False
