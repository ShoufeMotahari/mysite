# arvan_integration/downloader.py
import logging

from django.conf import settings

logger = logging.getLogger("arvan_integration")


def get_file_url(file_path):
    """
    Generate public URL for file
    :param file_path: File path inside bucket, e.g., avatars/profile.jpg
    :return: Public direct link to access the file
    """
    if not file_path:
        return None

    # Remove leading slash if present
    if file_path.startswith("/"):
        file_path = file_path[1:]

    # Use the custom domain for URL generation
    base_url = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}"
    full_url = f"{base_url}/{file_path}"

    logger.debug(f"Generated URL for {file_path}: {full_url}")
    return full_url


def get_file_download_url(file_path, expires_in=3600):
    """
    Generate a presigned URL for secure file download
    :param file_path: File path inside bucket
    :param expires_in: URL expiration time in seconds
    :return: Presigned URL
    """
    import boto3
    from botocore.exceptions import ClientError

    s3 = boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )

    try:
        url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.AWS_STORAGE_BUCKET_NAME, "Key": file_path},
            ExpiresIn=expires_in,
        )
        return url
    except ClientError as e:
        logger.error(f"Error generating presigned URL: {e}")
        return None
