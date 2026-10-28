import logging
from typing import Optional, Tuple
import httpx
from core.config import settings

logger = logging.getLogger(__name__)


class SupabaseStorageService:
    """
    Lightweight, asynchronous Supabase Storage client using REST API.
    Used for remote Vercel cloud deployments to store and stream private KYC identity documents.
    """

    def __init__(self):
        self.url = (settings.SUPABASE_URL or "").rstrip("/")
        self.key = settings.SUPABASE_KEY or ""
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}"
        }

    @property
    def is_configured(self) -> bool:
        return bool(self.url and self.key)

    async def ensure_bucket_exists(self, bucket_name: str = "kyc-documents", is_public: bool = False) -> bool:
        if not self.is_configured:
            return False

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # Check if bucket exists
                res = await client.get(f"{self.url}/storage/v1/bucket/{bucket_name}", headers=self.headers)
                if res.status_code == 200:
                    return True

                # Bucket does not exist, provision as private bucket
                payload = {
                    "id": bucket_name,
                    "name": bucket_name,
                    "public": is_public,
                    "file_size_limit": 5242880  # 5 MB
                }
                create_res = await client.post(
                    f"{self.url}/storage/v1/bucket",
                    headers=self.headers,
                    json=payload
                )
                if create_res.status_code in (200, 201):
                    logger.info("Successfully provisioned private Supabase Storage bucket '%s'", bucket_name)
                    return True
                else:
                    logger.warning("Could not auto-create bucket '%s': %s", bucket_name, create_res.text)
                    return False
            except Exception as e:
                logger.error("Supabase bucket verification error: %s", e)
                return False

    async def upload_file(
        self,
        bucket_name: str,
        object_path: str,
        content: bytes,
        mime_type: str = "application/octet-stream"
    ) -> bool:
        if not self.is_configured:
            return False

        clean_path = object_path.lstrip("/")
        headers = {
            **self.headers,
            "Content-Type": mime_type,
            "x-upsert": "true"
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                res = await client.post(
                    f"{self.url}/storage/v1/object/{bucket_name}/{clean_path}",
                    headers=headers,
                    content=content
                )
                if res.status_code in (200, 201):
                    logger.info("Successfully uploaded object to Supabase: %s/%s", bucket_name, clean_path)
                    return True
                else:
                    logger.error("Supabase storage upload failed with status %d: %s", res.status_code, res.text)
                    return False
            except Exception as e:
                logger.error("Supabase upload exception: %s", e)
                return False

    async def download_file(self, bucket_name: str, object_path: str) -> Optional[bytes]:
        if not self.is_configured:
            return None

        clean_path = object_path.lstrip("/")
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Private/authenticated object download
                res = await client.get(
                    f"{self.url}/storage/v1/object/authenticated/{bucket_name}/{clean_path}",
                    headers=self.headers
                )
                if res.status_code == 200:
                    return res.content
                else:
                    logger.error("Failed to download object from Supabase (HTTP %d): %s", res.status_code, res.text)
                    return None
            except Exception as e:
                logger.error("Supabase download exception: %s", e)
                return None

    async def delete_file(self, bucket_name: str, object_path: str) -> bool:
        if not self.is_configured:
            return False

        clean_path = object_path.lstrip("/")
        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                res = await client.delete(
                    f"{self.url}/storage/v1/object/{bucket_name}",
                    headers=self.headers,
                    json={"prefixes": [clean_path]}
                )
                if res.status_code == 200:
                    logger.info("Deleted object from Supabase: %s/%s", bucket_name, clean_path)
                    return True
                else:
                    logger.warning("Could not delete object from Supabase: %s", res.text)
                    return False
            except Exception as e:
                logger.error("Supabase delete exception: %s", e)
                return False


supabase_storage = SupabaseStorageService()
