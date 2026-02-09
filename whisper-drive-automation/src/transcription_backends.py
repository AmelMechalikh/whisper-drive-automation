"""
Transcription backend abstraction layer.

Supports multiple backends:
- cpu_local: Local CPU-based WhisperX alignment
- gpu_runpod: RunPod Serverless GPU-based Whisper Large-v3-turbo
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class TranscriptionBackend(ABC):
    """Base interface for transcription backends."""

    @abstractmethod
    def transcribe_audio(
        self,
        audio_path: str,
        language: str = "fr",
        word_timestamps: bool = True
    ) -> Dict:
        """
        Transcribe audio file to text with timestamps.

        Args:
            audio_path: Path to audio file
            language: Language code (default: 'fr')
            word_timestamps: Include word-level timestamps (default: True)

        Returns:
            Dict with 'segments' containing transcription results
        """
        pass

    @abstractmethod
    def align_segments(
        self,
        audio_path: str,
        segments: List[Dict],
        language: str = "fr"
    ) -> List[Dict]:
        """
        Align segments with word-level timestamps.

        Args:
            audio_path: Path to audio file
            segments: List of segment dicts with 'start', 'end', 'text'
            language: Language code (default: 'fr')

        Returns:
            List of aligned segments with word-level timestamps
        """
        pass

    @abstractmethod
    def get_backend_name(self) -> str:
        """Return backend identifier for logging."""
        pass


class CPULocalBackend(TranscriptionBackend):
    """Existing CPU-based WhisperX implementation."""

    def __init__(self, config: dict):
        self.config = config
        self.device = config.get('transcription_backend', {}).get('cpu_local', {}).get('device', 'cpu')
        self.compute_type = config.get('transcription_backend', {}).get('cpu_local', {}).get('compute_type', 'int8')
        self.model_name = config.get('transcription_backend', {}).get('cpu_local', {}).get('model', 'base')

        # Lazy import whisper and whisperx only when CPU backend is used
        try:
            import whisper
            import whisperx
            self.whisper = whisper
            self.whisperx = whisperx
        except ImportError:
            raise ImportError("whisper and whisperx are required for CPU backend")

        # Load Whisper model for transcription
        self.transcription_model = None

        logger.info(f"[CPU] Initialized CPU backend with device={self.device}, model={self.model_name}, compute_type={self.compute_type}")

    def transcribe_audio(
        self,
        audio_path: str,
        language: str = "fr",
        word_timestamps: bool = True
    ) -> Dict:
        """Transcribe audio using Whisper on CPU."""
        import time
        start_time = time.time()

        logger.info(f"[CPU] Transcribing audio: {audio_path}")

        # Load transcription model if not already loaded
        if self.transcription_model is None:
            logger.info(f"[CPU] Loading Whisper model: {self.model_name}")
            self.transcription_model = self.whisper.load_model(self.model_name, device=self.device)

        # Transcribe
        result = self.transcription_model.transcribe(
            audio_path,
            language=language,
            word_timestamps=word_timestamps,
            verbose=False
        )

        elapsed = time.time() - start_time
        logger.info(f"[CPU] Transcription completed in {elapsed:.2f}s")

        return result

    def align_segments(self, audio_path: str, segments: List[Dict], language: str = "fr") -> List[Dict]:
        """Align segments using WhisperX on CPU."""
        import time
        start_time = time.time()

        logger.info(f"[CPU] Loading alignment model for language: {language}")

        # Load alignment model
        model_a, metadata = self.whisperx.load_align_model(
            language_code=language,
            device=self.device
        )

        logger.info(f"[CPU] Aligning {len(segments)} segments...")

        # Load audio
        audio = self.whisperx.load_audio(audio_path)

        # Align segments
        result = self.whisperx.align(
            segments,
            model_a,
            metadata,
            audio,
            self.device,
            return_char_alignments=False
        )

        aligned_segments = result["segments"]

        elapsed = time.time() - start_time
        logger.info(f"[CPU] Alignment completed in {elapsed:.2f}s")

        return aligned_segments

    def get_backend_name(self) -> str:
        return "cpu_local"


class RunPodBackend(TranscriptionBackend):
    """GPU-based RunPod Serverless backend."""

    def __init__(self, config: dict):
        self.config = config
        runpod_config = config.get('transcription_backend', {}).get('gpu_runpod', {})

        self.api_endpoint = runpod_config.get('api_endpoint')
        if not self.api_endpoint:
            raise ValueError("RunPod api_endpoint not configured in highlight_config.json")

        # Get API key from environment variable
        import os
        api_key_env = runpod_config.get('api_key_env', 'RUNPOD_API_KEY')
        self.api_key = os.environ.get(api_key_env)
        if not self.api_key:
            raise ValueError(f"RunPod API key not found in environment variable: {api_key_env}")

        self.model = runpod_config.get('model', 'large-v3-turbo')
        self.timeout = runpod_config.get('timeout_seconds', 1800)  # 30 minutes for long audio files
        self.max_retries = runpod_config.get('max_retries', 3)

        logger.info(f"[RunPod] Initialized RunPod backend with model={self.model}, timeout={self.timeout}s")

    def transcribe_audio(
        self,
        audio_path: str,
        language: str = "fr",
        word_timestamps: bool = True
    ) -> Dict:
        """Transcribe audio using RunPod Serverless Whisper API."""
        import time
        from runpod_client import RunPodClient

        start_time = time.time()

        logger.info(f"[RunPod] Transcribing audio with {self.model}")

        # Upload audio to temporary location accessible by RunPod
        audio_url = self._upload_audio_for_runpod(audio_path)

        # Call RunPod API
        client = RunPodClient(api_key=self.api_key, endpoint=self.api_endpoint)

        try:
            result = client.transcribe_audio(
                audio_url=audio_url,
                model=self.model,
                language=language
            )

            elapsed = time.time() - start_time
            logger.info(f"[RunPod] Transcription completed in {elapsed:.2f}s")

            # Convert Faster Whisper format to Whisper-compatible format
            segments = result.get('segments', [])
            word_timestamps = result.get('word_timestamps', [])

            # Inject word timestamps into segments
            if word_timestamps:
                segments = self._inject_words_into_segments(segments, word_timestamps)

            # Return in Whisper-compatible format
            return {
                'text': result.get('transcription', ''),
                'segments': segments,
                'language': language
            }

        except Exception as e:
            logger.error(f"[RunPod] Transcription failed: {e}")
            raise

    def align_segments(self, audio_path: str, segments: List[Dict], language: str = "fr") -> List[Dict]:
        """
        Align segments using RunPod Serverless Whisper API.

        Note: RunPod transcribes from scratch, we don't actually "align" existing segments.
        We upload audio and get back word-level timestamps.
        """
        import time
        from runpod_client import RunPodClient

        start_time = time.time()

        logger.info(f"[RunPod] Uploading audio and requesting transcription with {self.model}")

        # Upload audio to temporary location accessible by RunPod
        audio_url = self._upload_audio_for_runpod(audio_path)

        # Call RunPod API
        client = RunPodClient(api_key=self.api_key, endpoint=self.api_endpoint)

        try:
            result = client.transcribe_audio(
                audio_url=audio_url,
                model=self.model,
                language=language
            )

            # Convert RunPod response to whisperx-compatible format
            aligned_segments = self._convert_runpod_to_whisperx_format(result)

            elapsed = time.time() - start_time
            logger.info(f"[RunPod] Transcription completed in {elapsed:.2f}s")

            return aligned_segments

        except Exception as e:
            logger.error(f"[RunPod] Transcription failed: {e}")
            raise

    def _upload_audio_for_runpod(self, audio_path: str) -> str:
        """
        Upload audio to accessible location and return URL.

        If input is a video file, extracts audio first.

        Options:
        1. Upload to GCS bucket with signed URL (recommended)
        2. Create temporary Drive shareable link

        For now, using GCS approach.
        """
        from google.cloud import storage
        import os
        import uuid
        import subprocess
        import tempfile

        # Check if file is video and needs audio extraction
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
        file_ext = os.path.splitext(audio_path)[1].lower()

        upload_path = audio_path
        temp_audio_file = None

        if file_ext in video_extensions:
            logger.info(f"[RunPod] Video file detected, extracting audio...")

            # Create temp file for extracted audio
            temp_audio_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_audio_path = temp_audio_file.name
            temp_audio_file.close()

            # Extract audio using ffmpeg
            cmd = [
                'ffmpeg',
                '-i', audio_path,
                '-vn',  # No video
                '-acodec', 'pcm_s16le',  # PCM 16-bit
                '-ar', '16000',  # 16kHz sample rate
                '-ac', '1',  # Mono
                '-y',  # Overwrite
                temp_audio_path
            ]

            try:
                subprocess.run(cmd, check=True, capture_output=True)
                logger.info(f"[RunPod] Audio extracted to {temp_audio_path}")
                upload_path = temp_audio_path
            except subprocess.CalledProcessError as e:
                logger.error(f"[RunPod] Failed to extract audio: {e.stderr.decode() if e.stderr else 'Unknown error'}")
                if os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)
                raise Exception(f"Failed to extract audio from video: {e}")

        # Get bucket name from config or use default
        bucket_name = self.config.get('gcs_temp_bucket', 'whisper-temp-audio')

        # Upload to GCS with unique name
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)

        # Use .wav extension for extracted audio
        base_name = os.path.basename(upload_path)
        blob_name = f"temp-audio/{uuid.uuid4()}/{base_name}"
        blob = bucket.blob(blob_name)

        logger.info(f"[RunPod] Uploading {upload_path} to gs://{bucket_name}/{blob_name}")
        blob.upload_from_filename(upload_path)

        # Clean up temp audio file if created
        if temp_audio_file and os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
            logger.info(f"[RunPod] Cleaned up temp audio file")

        # Generate signed URL - use public access as workaround for Cloud Run credentials issue
        # Cloud Run compute credentials can't sign URLs, so make blob temporarily public
        logger.info(f"[RunPod] Making blob public for RunPod access (auto-cleanup after 1 day)")
        blob.make_public()
        url = blob.public_url

        logger.info(f"[RunPod] Public URL generated: {url}")

        return url

    def _convert_runpod_to_whisperx_format(self, runpod_result: Dict) -> List[Dict]:
        """
        Convert RunPod API response to whisperx-compatible segment format.

        Expected whisperx format:
        {
            "start": float,
            "end": float,
            "text": str,
            "words": [
                {"start": float, "end": float, "word": str, "score": float}
            ]
        }
        """
        segments = []

        # RunPod should return segments in similar format
        # Adjust mapping based on actual RunPod response structure
        for seg in runpod_result.get('segments', []):
            segment = {
                'start': seg.get('start'),
                'end': seg.get('end'),
                'text': seg.get('text', '').strip()
            }

            # Add word-level timestamps if available
            if 'words' in seg:
                segment['words'] = [
                    {
                        'start': w.get('start'),
                        'end': w.get('end'),
                        'word': w.get('word', '').strip(),
                        'score': w.get('confidence', 1.0)
                    }
                    for w in seg['words']
                ]

            segments.append(segment)

        logger.info(f"[RunPod] Converted {len(segments)} segments to whisperx format")
        return segments

    def _inject_words_into_segments(self, segments: List[Dict], word_timestamps: List[Dict]) -> List[Dict]:
        """
        Inject word timestamps into segments.

        Faster Whisper returns word_timestamps as a flat list, but we need them
        grouped by segment for compatibility with WhisperX format.

        Args:
            segments: List of segments with start/end/text
            word_timestamps: Flat list of all words with start/end/word

        Returns:
            Segments with words injected
        """
        if not segments or not word_timestamps:
            return segments

        # Make a copy to avoid modifying the original
        segments_with_words = []
        word_idx = 0

        for segment in segments:
            seg_start = segment.get('start', 0)
            seg_end = segment.get('end', 0)

            # Find all words that belong to this segment
            segment_words = []
            while word_idx < len(word_timestamps):
                word = word_timestamps[word_idx]
                word_start = word.get('start', 0)

                # If word starts before segment ends, it belongs to this segment
                if word_start < seg_end:
                    segment_words.append({
                        'start': word.get('start'),
                        'end': word.get('end'),
                        'word': word.get('word', ''),
                        'score': 1.0  # Faster Whisper doesn't provide confidence scores
                    })
                    word_idx += 1
                else:
                    break

            # Add segment with words
            segment_copy = segment.copy()
            if segment_words:
                segment_copy['words'] = segment_words
            segments_with_words.append(segment_copy)

        logger.info(f"[RunPod] Injected words into {len(segments_with_words)} segments")
        return segments_with_words

    def get_backend_name(self) -> str:
        return "gpu_runpod"


def get_transcription_backend(config: dict) -> TranscriptionBackend:
    """
    Factory function to select transcription backend.

    Args:
        config: Configuration dict from highlight_config.json

    Returns:
        Appropriate TranscriptionBackend instance
    """
    backend_type = config.get('transcription_backend', {}).get('provider', 'cpu_local')

    logger.info(f"Selecting transcription backend: {backend_type}")

    if backend_type == 'gpu_runpod':
        return RunPodBackend(config)
    elif backend_type == 'cpu_local':
        return CPULocalBackend(config)
    else:
        raise ValueError(f"Unknown transcription backend: {backend_type}. Must be 'cpu_local' or 'gpu_runpod'")
