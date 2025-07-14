# arvan_integration/services.py
from arvan_integration.uploader import upload_file
from arvan_integration.remover import delete_file
from arvan_integration.downloader import get_file_url, get_file_download_url
from django.core.files.storage import default_storage
import logging

logger = logging.getLogger('arvan_integration')

class ArvanService:

    @staticmethod
    def upload(file_obj, path="uploads/"):
        """
        Upload file to specified path in Arvan
        Returns: (url, file_path)
        """
        try:
            return upload_file(file_obj, path)
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            raise

    @staticmethod
    def delete(file_path):
        """
        Delete file from Arvan
        """
        try:
            return delete_file(file_path)
        except Exception as e:
            logger.error(f"Delete failed: {e}")
            return False

    @staticmethod
    def get_url(file_path):
        """
        Get public URL for file
        """
        return get_file_url(file_path)

    @staticmethod
    def get_download_url(file_path, expires_in=3600):
        """
        Get presigned download URL for file
        """
        return get_file_download_url(file_path, expires_in)

    @staticmethod
    def file_exists(file_path):
        """
        Check if file exists in storage
        """
        return default_storage.exists(file_path)

    @staticmethod
    def get_file_size(file_path):
        """
        Get file size in bytes
        """
        try:
            return default_storage.size(file_path)
        except Exception as e:
            logger.error(f"Error getting file size: {e}")
            return 0
