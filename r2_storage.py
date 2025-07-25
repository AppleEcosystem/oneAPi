import boto3
from typing import Optional, BinaryIO
from botocore.exceptions import ClientError
from config import Config

class R2Storage:
    """Cloudflare R2 storage client (using B2 backend)"""
    
    def __init__(self):
        config = Config()
        self.endpoint_url = config.B2_ENDPOINT_URL
        self.aws_access_key_id = config.B2_ACCESS_KEY_ID
        self.aws_secret_access_key = config.B2_SECRET_ACCESS_KEY
        self.region_name = config.B2_REGION_NAME
        self.bucket_name = config.B2_BUCKET_NAME
        self.public_url_base = config.B2_PUBLIC_URL_BASE
        
        self.client = boto3.client(
            's3',
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.region_name
        )
    
    async def upload_file(self, file_data: bytes, file_key: str, content_type: str = "application/octet-stream") -> bool:
        """Upload file to R2 storage"""
        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=file_key,
                Body=file_data,
                ContentType=content_type
            )
            return True
        except ClientError as e:
            return False
    
    async def delete_file(self, file_key: str) -> bool:
        """Delete file from R2 storage"""
        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=file_key
            )
            return True
        except ClientError as e:
            return False
    
    def get_public_url(self, file_key: str) -> str:
        """Get public URL for a file"""
        return f"{self.public_url_base}/{file_key}"
    
    async def file_exists(self, file_key: str) -> bool:
        """Check if file exists in R2"""
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=file_key)
            return True
        except ClientError:
            return False
