import os
from os.path import join
import uuid
import boto3
import boto3.session


def upload_file_to_s3(
    file_path: str,
    key: str,
):
    bucket_name = os.getenv("S3_BUCKET_NAME")

    session = boto3.Session()
    s3_client = session.client("s3")

    response = s3_client.upload_file(file_path, bucket_name, key)

    if response is not None:
        raise Exception(f"Failed to upload to S3. Response: {response}")

    return key


def upload_audio_data_to_s3(
    audio_data: bytes,
    key: str,
):
    """
    Upload audio data to S3 bucket

    Args:
        audio_data: Audio data in bytes
        key: S3 key ending in .wav

    Returns:
        str: The S3 key where the audio was uploaded
    """
    if not key.endswith(".wav"):
        raise ValueError("Key must end with .wav extension")

    bucket_name = os.getenv("S3_BUCKET_NAME")

    session = boto3.Session()
    s3_client = session.client("s3")

    response = s3_client.put_object(
        Bucket=bucket_name, Key=key, Body=audio_data, ContentType="audio/wav"
    )

    status_code = response["ResponseMetadata"]["HTTPStatusCode"]
    if status_code != 200:
        raise Exception(f"Failed to upload to S3. Status code: {status_code}")

    return key


def download_file_from_s3_as_bytes(key: str):
    """
    Download a file from S3 bucket
    """
    bucket_name = os.getenv("S3_BUCKET_NAME")
    session = boto3.Session()
    s3_client = session.client("s3")

    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    return response["Body"].read()


def get_audio_upload_s3_dir():
    root_dir = os.getenv("S3_FOLDER_NAME")
    return join(root_dir, "media", "audio")


def generate_s3_uuid():
    return str(uuid.uuid4())


def get_audio_upload_s3_key(uuid: str):
    return join(get_audio_upload_s3_dir(), f"{uuid}.wav")
