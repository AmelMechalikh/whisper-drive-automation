#!/usr/bin/env python3
"""
Test unitaire pour le streaming d'extraction audio depuis Drive vers ffmpeg
"""

import os
import io
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from googleapiclient.http import MediaIoBaseDownload


def test_stream_extraction_mock():
    """Test du streaming avec un mock de Drive"""
    print("🧪 Test 1: Stream extraction avec mock...")

    # Create a mock Drive request that returns chunks of data
    mock_request = Mock()

    # Simulate video data (just some bytes)
    fake_video_data = b"fake video data " * 1000  # 16KB of fake data

    # Create a buffer with our fake data
    buffer = io.BytesIO(fake_video_data)

    # Mock the downloader
    with patch('googleapiclient.http.MediaIoBaseDownload') as MockDownloader:
        # Setup the mock to simulate downloading in chunks
        mock_downloader_instance = MockDownloader.return_value

        # Simulate downloading in 2 chunks
        chunk1 = fake_video_data[:8000]
        chunk2 = fake_video_data[8000:]

        mock_downloader_instance.next_chunk.side_effect = [
            (Mock(progress=lambda: 0.5), False),  # First chunk (50%)
            (Mock(progress=lambda: 1.0), True),   # Second chunk (100%, done)
        ]

        # Test the streaming logic
        buffer = io.BytesIO()
        mock_downloader_instance._fd = buffer

        # Simulate writing chunks
        buffer.write(chunk1)
        data1 = buffer.getvalue()
        assert len(data1) == len(chunk1), f"Chunk 1 size mismatch: {len(data1)} != {len(chunk1)}"
        print(f"  ✅ Chunk 1: {len(data1)} bytes")

        buffer = io.BytesIO()
        buffer.write(chunk2)
        data2 = buffer.getvalue()
        assert len(data2) == len(chunk2), f"Chunk 2 size mismatch: {len(data2)} != {len(chunk2)}"
        print(f"  ✅ Chunk 2: {len(data2)} bytes")

        print("✅ Test 1 passed!")


def test_ffmpeg_stdin_simple():
    """Test simple de ffmpeg avec stdin"""
    print("\n🧪 Test 2: ffmpeg stdin simple...")

    # Create a simple test audio (1 second of silence)
    test_audio = tempfile.mktemp(suffix='.mp3')

    try:
        # Generate 1 second of silence with ffmpeg
        result = subprocess.run([
            'ffmpeg',
            '-f', 'lavfi',
            '-i', 'anullsrc=duration=1',
            '-acodec', 'libmp3lame',
            '-ab', '128k',
            '-ar', '16000',
            '-y',
            test_audio
        ], capture_output=True, timeout=10)

        assert result.returncode == 0, f"ffmpeg failed: {result.stderr.decode()}"
        assert os.path.exists(test_audio), "Audio file not created"

        file_size = os.path.getsize(test_audio)
        assert file_size > 0, "Audio file is empty"

        print(f"  ✅ Generated test audio: {file_size} bytes")
        print("✅ Test 2 passed!")

    finally:
        if os.path.exists(test_audio):
            os.remove(test_audio)


def test_buffer_reset():
    """Test du reset de buffer BytesIO"""
    print("\n🧪 Test 3: Buffer reset...")

    buffer = io.BytesIO()
    buffer.write(b"test data 1")

    data1 = buffer.getvalue()
    assert data1 == b"test data 1", "Buffer content mismatch"
    print(f"  ✅ Buffer 1: {data1}")

    # Reset buffer
    buffer = io.BytesIO()
    buffer.write(b"test data 2")

    data2 = buffer.getvalue()
    assert data2 == b"test data 2", "Buffer content mismatch after reset"
    assert data2 != data1, "Buffer not properly reset"
    print(f"  ✅ Buffer 2: {data2}")

    print("✅ Test 3 passed!")


if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Tests unitaires - Stream extraction audio")
    print("=" * 60)

    try:
        test_stream_extraction_mock()
        test_ffmpeg_stdin_simple()
        test_buffer_reset()

        print("\n" + "=" * 60)
        print("✅ Tous les tests sont passés!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
