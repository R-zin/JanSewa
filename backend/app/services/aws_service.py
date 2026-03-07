import boto3
from botocore.exceptions import ClientError
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class AWSService:
    """AWS service integration"""
    
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )
        self.bucket_name = settings.S3_BUCKET_NAME
    
    async def upload_document(self, file_data: bytes, s3_key: str) -> bool:
        """Upload encrypted document to S3"""
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_data,
                ServerSideEncryption='AES256'
            )
            logger.info(f"Document uploaded to S3: {s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to upload document: {e}")
            return False
    
    async def download_document(self, s3_key: str) -> bytes:
        """Download document from S3"""
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return response['Body'].read()
        except ClientError as e:
            logger.error(f"Failed to download document: {e}")
            raise
    
    async def delete_document(self, s3_key: str) -> bool:
        """Delete document from S3"""
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            logger.info(f"Document deleted from S3: {s3_key}")
            return True
        except ClientError as e:
            logger.error(f"Failed to delete document: {e}")
            return False


aws_service = AWSService()
