import os
from phoenix import Client
from api.settings import settings


def get_raw_traces():
    os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = settings.phoenix_endpoint
    os.environ["PHOENIX_API_KEY"] = settings.phoenix_api_key

    project_name = f"sensai-{settings.env}"
    return Client().get_spans_dataframe(project_name=project_name)
