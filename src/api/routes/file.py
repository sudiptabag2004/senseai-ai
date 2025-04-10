import traceback
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import boto3
from botocore.exceptions import ClientError
from api.settings import settings
from api.utils.logging import logger
from api.utils.s3 import (
    generate_s3_uuid,
    get_media_upload_s3_key,
)
from api.models import (
    PresignedUrlRequest,
    PresignedUrlResponse,
    S3FetchPresignedUrlResponse,
)

router = APIRouter()


@router.put("/presigned-url/create", response_model=PresignedUrlResponse)
async def get_presigned_url(request: PresignedUrlRequest) -> PresignedUrlResponse:
    try:
        s3_client = boto3.client(
            "s3",
            region_name="ap-south-1",
            config=boto3.session.Config(signature_version="s3v4"),
        )

        uuid = generate_s3_uuid()
        key = get_media_upload_s3_key(uuid, request.content_type.split("/")[1])

        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.s3_bucket_name,
                "Key": key,
                "ContentType": request.content_type,
            },
            ExpiresIn=600,  # URL expires in 1 hour
        )

        return {
            "presigned_url": presigned_url,
            "file_key": key,
            "file_uuid": uuid,
        }

    except ClientError as e:
        logger.error(f"Error generating presigned URL: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate presigned URL")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="An unexpected error occurred")


@router.get("/presigned-url/get")
async def get_download_presigned_url(
    uuid: str,
    file_extension: str,
) -> S3FetchPresignedUrlResponse:
    try:
        s3_client = boto3.client(
            "s3",
            region_name="ap-south-1",
            config=boto3.session.Config(signature_version="s3v4"),
        )

        key = get_media_upload_s3_key(uuid, file_extension)

        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.s3_bucket_name,
                "Key": key,
            },
            ExpiresIn=600,  # URL expires in 1 hour
        )

        return {"url": presigned_url}

    except ClientError as e:
        logger.error(f"Error generating download presigned URL: {str(e)}")
        raise HTTPException(
            status_code=500, detail="Failed to generate download presigned URL"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="An unexpected error occurred")
