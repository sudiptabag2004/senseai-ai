import os
from datetime import datetime, timedelta
from typing import Optional
from datetime import datetime, timedelta
import pandas as pd
from phoenix import Client
from api.settings import settings


def get_raw_traces(
    filter_period: Optional[str] = None, timeout: int = 120
) -> pd.DataFrame:
    os.environ["PHOENIX_COLLECTOR_ENDPOINT"] = settings.phoenix_endpoint
    os.environ["PHOENIX_API_KEY"] = settings.phoenix_api_key
    project_name = f"sensai-{settings.env}"

    if not filter_period:
        return Client().get_spans_dataframe(project_name=project_name, timeout=timeout)

    if filter_period not in ["last_day", "current_month", "current_year"]:
        raise ValueError("Invalid filter period")

    if filter_period == "last_day":
        end_time = datetime.now()
        start_time = end_time - timedelta(days=1)
        return Client().get_spans_dataframe(
            project_name=project_name,
            start_time=start_time,
            end_time=end_time,
            timeout=timeout,
        )

    if filter_period == "current_month":
        end_time = datetime.now()
        start_time = end_time.replace(day=1)
        return Client().get_spans_dataframe(
            project_name=project_name,
            start_time=start_time,
            end_time=end_time,
            timeout=timeout,
        )

    end_time = datetime.now()
    start_time = end_time.replace(month=1, day=1)
    return Client().get_spans_dataframe(
        project_name=project_name,
        start_time=start_time,
        end_time=end_time,
        timeout=timeout,
    )
