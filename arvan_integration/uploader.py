# arvan_integration/uploader.py
import boto3
import uuid
import os
from django.conf import settings
from botocore.exceptions import ClientError
from django.core.files.storage import default_storage
import logging

logger = logging.getLogger('arvan_integration')


def upload_file(file_obj, path="uploads/"):
    """
    Upload file to Arvan Cloud with collision handling
    """
    s3 = boto3.client(
        's3',
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )

    # Generate unique filename to avoid collisions
    file_name, file_extension = os.path.splitext(file_obj.name)
    unique_filename = f"{file_name}_{uuid.uuid4().hex[:8]}{file_extension}"
    full_path = f"{path}{unique_filename}"

    try:
        # Upload file
        s3.upload_fileobj(
            file_obj,
            settings.AWS_STORAGE_BUCKET_NAME,
            full_path,
            ExtraArgs={'ACL': 'public-read'}  # Make file publicly readable
        )

        # Return the correct URL
        url = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/{full_path}"
        logger.info(f"File uploaded successfully: {full_path}")
        return url, full_path

    except ClientError as e:
        logger.error(f"Error uploading file: {e}")
        raise Exception(f"خطا در آپلود فایل: {e}")


def get_unique_filename(original_name, path="uploads/"):
    """
    Generate unique filename to avoid collisions
    """
    file_name, file_extension = os.path.splitext(original_name)
    unique_filename = f"{file_name}_{uuid.uuid4().hex[:8]}{file_extension}"
    return f"{path}{unique_filename}"