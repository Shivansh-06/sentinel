import logging

logger = logging.getLogger(__name__)


def process_job(job_id: str) -> None:
    """
    Main processing pipeline for a submitted job.
    Phases 3-5 will fill this in.
    """
    logger.info(f"Processing job {job_id}")
    print(f"[Worker] Picked up job: {job_id}")