import os


def get_api_base_url() -> str:
    value = os.environ.get("API_BASE_URL")
    if not value:
        raise RuntimeError(
            "API_BASE_URL environment variable is required to reach itsm-api"
        )
    return value
