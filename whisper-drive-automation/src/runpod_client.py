"""
RunPod Serverless API client for Whisper transcription.

Handles:
- Job submission to RunPod endpoint
- Polling job status until completion
- Error handling and timeouts
"""

import requests
import time
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class RunPodClient:
    """Client for RunPod Serverless API."""

    def __init__(self, api_key: str, endpoint: str):
        """
        Initialize RunPod client.

        Args:
            api_key: RunPod API key
            endpoint: RunPod endpoint URL (e.g., https://api.runpod.ai/v2/<ENDPOINT_ID>)
        """
        self.api_key = api_key
        self.endpoint = endpoint.rstrip('/')  # Remove trailing slash if present
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        logger.info(f"RunPod client initialized for endpoint: {endpoint}")

    def transcribe_audio(
        self,
        audio_url: str,
        model: str = "large-v3-turbo",
        language: str = "fr"
    ) -> Dict:
        """
        Send audio to RunPod for transcription.

        Args:
            audio_url: Publicly accessible URL to audio file
            model: Whisper model to use (default: large-v3-turbo)
            language: Language code (default: fr)

        Returns:
            Transcription result with segments and word-level timestamps

        Raises:
            requests.HTTPError: If API call fails
            TimeoutError: If job doesn't complete within timeout
            Exception: If job fails on RunPod side
        """
        logger.info(f"Submitting transcription job to RunPod (model={model}, language={language})")

        payload = {
            "input": {
                "audio": audio_url,
                "model": model,
                "language": language,
                "word_timestamps": True
            }
        }

        # Submit job to RunPod
        try:
            response = requests.post(
                f"{self.endpoint}/run",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to submit RunPod job: {e}")
            raise

        result = response.json()
        job_id = result.get('id')

        if not job_id:
            raise Exception(f"RunPod did not return job ID. Response: {result}")

        logger.info(f"RunPod job submitted successfully. Job ID: {job_id}")

        # Poll for results
        return self._poll_job_status(job_id)

    def _poll_job_status(self, job_id: str, timeout: int = 1800, poll_interval: int = 5) -> Dict:
        """
        Poll job status until completion.

        Args:
            job_id: RunPod job ID
            timeout: Maximum time to wait in seconds (default: 1800 = 30 min)
            poll_interval: Time between status checks in seconds (default: 5)

        Returns:
            Job output/result

        Raises:
            TimeoutError: If job doesn't complete within timeout
            Exception: If job fails
        """
        start_time = time.time()
        elapsed = 0

        logger.info(f"Polling job {job_id} (timeout={timeout}s, interval={poll_interval}s)")

        while elapsed < timeout:
            try:
                response = requests.get(
                    f"{self.endpoint}/status/{job_id}",
                    headers=self.headers,
                    timeout=30
                )
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                logger.warning(f"Error checking job status: {e}. Retrying...")
                time.sleep(poll_interval)
                elapsed = time.time() - start_time
                continue

            data = response.json()
            status = data.get('status')

            if status == 'COMPLETED':
                logger.info(f"Job {job_id} completed successfully")
                output = data.get('output')

                if not output:
                    raise Exception(f"Job completed but no output returned. Response: {data}")

                return output

            elif status == 'FAILED':
                error_msg = data.get('error', 'Unknown error')
                logger.error(f"Job {job_id} failed: {error_msg}")
                raise Exception(f"RunPod job failed: {error_msg}")

            elif status in ['IN_QUEUE', 'IN_PROGRESS']:
                elapsed = time.time() - start_time
                logger.debug(f"Job {job_id} status: {status} ({elapsed:.1f}s elapsed)")

            else:
                logger.warning(f"Unknown job status: {status}")

            time.sleep(poll_interval)
            elapsed = time.time() - start_time

        # Timeout reached
        logger.error(f"Job {job_id} timed out after {timeout}s")
        raise TimeoutError(f"RunPod job {job_id} timed out after {timeout}s")

    def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.

        Args:
            job_id: RunPod job ID

        Returns:
            True if cancellation successful
        """
        try:
            response = requests.post(
                f"{self.endpoint}/cancel/{job_id}",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            logger.info(f"Job {job_id} cancelled successfully")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False
