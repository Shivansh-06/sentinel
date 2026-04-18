import redis
from rq import Queue

from app.config import settings


redis_conn = redis.Redis.from_url(settings.redis_url, decode_responses=False)

ingestion_queue = Queue("ingestion", connection=redis_conn)