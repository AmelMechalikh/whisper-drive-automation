#!/usr/bin/env python3
"""
HTTP wrapper for RunPod transcription worker to run on Cloud Run
Runs the worker in a background thread and provides health check endpoint
"""
import os
import threading
import logging
from flask import Flask, jsonify

# Import the main worker function
import sys
from pathlib import Path
current_dir = Path(__file__).parent.parent
sys.path.insert(0, str(current_dir / 'scripts'))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)

# Global variable to track worker status
worker_status = {
    'running': False,
    'error': None,
    'started_at': None
}


def run_worker():
    """Run the transcription worker in background"""
    from datetime import datetime
    import runpod_transcription_worker

    worker_status['running'] = True
    worker_status['started_at'] = datetime.now().isoformat()

    try:
        logger.info("Starting RunPod transcription worker in background thread...")
        runpod_transcription_worker.main()
    except Exception as e:
        logger.error(f"Worker error: {e}")
        worker_status['error'] = str(e)
        worker_status['running'] = False


@app.route('/')
def index():
    """Health check endpoint"""
    return jsonify({
        'service': 'runpod-transcription-worker',
        'status': 'healthy',
        'worker_running': worker_status['running'],
        'started_at': worker_status['started_at'],
        'error': worker_status['error']
    })


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'ok'}), 200


@app.route('/status')
def status():
    """Worker status endpoint"""
    return jsonify(worker_status)


if __name__ == '__main__':
    # Start worker in background thread
    worker_thread = threading.Thread(target=run_worker, daemon=True)
    worker_thread.start()

    # Start Flask server
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Starting HTTP server on port {port}")
    app.run(host='0.0.0.0', port=port, threaded=True)
