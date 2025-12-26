"""Storage service with MinIO using boto3."""

import uuid
from typing import Literal

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from config import settings
from logging_config import get_logger

logger = get_logger(__name__)

EntityType = Literal["products", "variants", "options"]
ALLOWED_CONTENT_TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif"]


class StorageService:
    """Service to manage files in MinIO/S3."""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        """Lazy initialization of boto3 client."""
        if self._client is None:
            self._client = boto3.client(
                "s3",
                endpoint_url=settings.minio_endpoint,
                aws_access_key_id=settings.minio_access_key,
                aws_secret_access_key=settings.minio_secret_key,
                config=Config(signature_version="s3v4"),
                region_name="us-east-1",  # MinIO ignores this but boto3 requires it
            )
            self._ensure_bucket_exists()
        return self._client

    def _ensure_bucket_exists(self) -> None:
        """Create the bucket if it doesn't exist."""
        try:
            self._client.head_bucket(Bucket=settings.minio_bucket)
        except ClientError:
            logger.info(f"Creating bucket: {settings.minio_bucket}")
            self._client.create_bucket(Bucket=settings.minio_bucket)

    def generate_upload_url(
        self,
        entity_type: EntityType,
        entity_id: str,
        content_type: str = "image/jpeg",
    ) -> dict:
        """
        Generate a presigned URL for uploading an image.

        Args:
            entity_type: Entity type (products, variants, options)
            entity_id: Entity ID
            content_type: File MIME type

        Returns:
            Dict with upload_url, file_key and expires_in
        """
        # Generate unique key to avoid collisions and cache issues
        file_ext = content_type.split("/")[-1]
        file_key = f"{entity_type}/{entity_id}/{uuid.uuid4().hex}.{file_ext}"

        presigned_url = self.client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.minio_bucket,
                "Key": file_key,
                "ContentType": content_type,
            },
            ExpiresIn=settings.minio_presigned_url_expiry,
            HttpMethod="PUT",
        )

        return {
            "upload_url": presigned_url,
            "file_key": file_key,
            "expires_in": settings.minio_presigned_url_expiry,
        }

    def generate_download_url(self, file_key: str) -> str | None:
        """
        Generate a presigned URL for downloading a file.

        Args:
            file_key: File key in the bucket

        Returns:
            Presigned URL or None if the file doesn't exist
        """
        if not file_key or not self.file_exists(file_key):
            return None

        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.minio_bucket, "Key": file_key},
            ExpiresIn=settings.minio_download_url_expiry,
        )

    def file_exists(self, file_key: str) -> bool:
        """
        Check if a file exists in the bucket.

        Args:
            file_key: File key

        Returns:
            True if exists, False otherwise
        """
        try:
            self.client.head_object(Bucket=settings.minio_bucket, Key=file_key)
            return True
        except ClientError:
            return False

    def delete_file(self, file_key: str) -> bool:
        """
        Delete a file from the bucket.

        Args:
            file_key: File key to delete

        Returns:
            True if deleted successfully
        """
        try:
            self.client.delete_object(Bucket=settings.minio_bucket, Key=file_key)
            logger.info(f"File deleted: {file_key}")
            return True
        except ClientError as e:
            logger.error(f"Error deleting file {file_key}: {e}")
            return False


# Singleton service instance
storage_service = StorageService()
