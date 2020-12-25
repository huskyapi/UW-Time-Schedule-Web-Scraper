import json
import sys
import logging
import httpx
import redis

# host = os.environ.get("REDIS_HOST"),
# port = os.environ.get("REDIS_PORT"),
# password = os.environ.get("REDIS_PASSWORD"),
log = logging.getLogger(__name__)


def redis_connect():
    log.info("connecting to redis server")
    try:
        redis_client = redis.Redis(
            host="localhost",
            port="6379",
            db=0,
            socket_timeout=5)
        ping = redis_client.ping()
        if ping:
            return redis_client
    except redis.AuthenticationError as e:
        print(f"Authentication error: {e}")
        sys.exit(1)


client = redis_connect()


def get_data_from_api(first_name, last_name):
    log.info(f"getting data from api for {first_name}, {last_name}")
    with httpx.Client() as http_client:
        base_url = "http://www.uwfaculty-lmao.tk/faculty/api/v1/"
        if not last_name:
            url = f"{base_url}{first_name}"
        else:
            url = f"{base_url}{first_name}%20{last_name}"

        log.info(f"getting API response from {url}")
        response = http_client.get(url)
        return response.json()


def get_data_from_cache(key: str):
    val = client.get(key)
    return val


def set_data_to_cache(key: str, value: str) -> bool:
    success = client.set(key, value=value)
    return success


def get_data(first_name, last_name):
    key = f"{first_name} {last_name}"
    data = get_data_from_cache(key)
    if data:
        log.info("data already exists in redis cache")
        data = json.loads(data)
        data["cache"] = True
    else:
        log.info("data does not already exist in redis cache")
        data = get_data_from_api(first_name, last_name)
        if data and data.get('teacher'):
            data["cache"] = False
            data = json.dumps(data)
            success = set_data_to_cache(key=key, value=data)
            if success:
                log.info("successfully added data to redis cache")
                return json.loads(data)
    log.info(f"data for {first_name} {last_name}: {data}")
    return data
