from flask import Flask, request, jsonify
import wave
import struct
from opuslib import Decoder
from io import BytesIO
import os
from datetime import datetime
from threading import Thread
from queue import Queue
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Queue for background processing
processing_queue = Queue()

class OpusToWavConverter:
    def __init__(self, sample_rate=16000, channels=1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.decoder = Decoder(sample_rate, channels)
        logger.debug(f"Initialized OpusToWavConverter with sample_rate={sample_rate}, channels={channels}")
        
    def _read_frame_length(self, data, offset):
        """Read 2-byte length header (little-endian)"""
        length = data[offset] | (data[offset + 1] << 8)
        logger.debug(f"Read frame length: {length} at offset: {offset}")
        return length
    
    def convert_to_wav(self, opus_data):
        """Convert Opus frames to WAV format"""
        logger.debug(f"Starting conversion of opus data, size: {len(opus_data)} bytes")
        wav_buffer = BytesIO()
        
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)  # 16-bit audio
            wav_file.setframerate(self.sample_rate)
            logger.debug(f"Initialized WAV file with channels={self.channels}, sample_width=2, framerate={self.sample_rate}")
            
            offset = 0
            frame_count = 0
            while offset < len(opus_data):
                if offset + 2 > len(opus_data):
                    logger.debug("Reached end of opus data while reading frame length")
                    break
                    
                frame_length = self._read_frame_length(opus_data, offset)
                offset += 2
                
                if offset + frame_length > len(opus_data):
                    logger.debug(f"Incomplete frame data at offset {offset}, expected length {frame_length}")
                    break
                    
                frame = opus_data[offset:offset + frame_length]
                offset += frame_length
                
                try:
                    # 20ms of audio at 16kHz = 320 samples
                    pcm = self.decoder.decode(bytes(frame), 320)
                    wav_data = struct.pack('<%dh' % (len(pcm) // 2), *struct.unpack('<%dh' % (len(pcm) // 2), pcm))
                    wav_file.writeframes(wav_data)
                    frame_count += 1
                    logger.debug(f"Successfully decoded frame {frame_count}, size: {len(wav_data)} bytes")
                except Exception as e:
                    logger.error(f"Error decoding frame {frame_count}: {e}")
                    continue
        
        final_size = wav_buffer.tell()
        logger.debug(f"Conversion complete. Processed {frame_count} frames, final WAV size: {final_size} bytes")
        return wav_buffer.getvalue()

def process_audio_data(opus_data, is_user):
    """Background processing function"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        prefix = 'user' if is_user else 'ai'
        logger.debug(f"Starting audio processing for {prefix} at {timestamp}")
        
        # Convert to WAV
        logger.debug(f"Converting opus data of size {len(opus_data)} bytes")
        wav_data = converter.convert_to_wav(opus_data)
        
        # Save WAV file
        filename = f'{prefix}_{timestamp}.wav'
        os.makedirs('recordings', exist_ok=True)
        
        with open(os.path.join('recordings', filename), 'wb') as f:
            f.write(wav_data)
            
        logger.info(f"Successfully processed and saved {filename}")
        logger.debug(f"Saved WAV file {filename}, size: {len(wav_data)} bytes")
            
    except Exception as e:
        logger.error(f"Error in background processing: {e}")
        logger.debug(f"Stack trace for background processing error:", exc_info=True)

def background_worker():
    """Worker thread to process queued audio data"""
    logger.debug("Starting background worker thread")
    while True:
        try:
            opus_data, is_user = processing_queue.get()
            logger.debug(f"Got new task from queue, data size: {len(opus_data)}, is_user: {is_user}")
            process_audio_data(opus_data, is_user)
            processing_queue.task_done()
            logger.debug("Task completed successfully")
        except Exception as e:
            logger.error(f"Error in background worker: {e}")
            logger.debug("Stack trace for worker error:", exc_info=True)

app = Flask(__name__)
converter = OpusToWavConverter()
logger.debug("Flask app and converter initialized")

# Start background worker thread
worker_thread = Thread(target=background_worker, daemon=True)
worker_thread.start()
logger.debug("Background worker thread started")

@app.route('/api/audio', methods=['POST'])
def receive_audio():
    logger.debug(f"Received audio request, content-type: {request.content_type}")
    
    if request.content_type != 'audio/opus':
        logger.warning(f"Invalid content type: {request.content_type}")
        return jsonify({'error': 'Invalid content type'}), 415
        
    try:
        opus_data = request.get_data()
        logger.debug(f"Received opus data, size: {len(opus_data)} bytes")
        
        if not opus_data:
            logger.warning("No data received in request")
            return jsonify({'error': 'No data received'}), 400
            
        # Quick validation of data format
        if len(opus_data) < 2:
            logger.warning(f"Invalid data format, data size: {len(opus_data)}")
            return jsonify({'error': 'Invalid data format'}), 400
            
        # Determine if it's user or AI audio
        is_user = 'user' in request.headers.get('X-Audio-Type', '').lower()
        logger.debug(f"Audio type: {'user' if is_user else 'ai'}, X-Audio-Type header: {request.headers.get('X-Audio-Type')}")
        
        # Queue the data for background processing
        processing_queue.put((opus_data, is_user))
        logger.debug(f"Added task to queue, current queue size: {processing_queue.qsize()}")
        
        # Immediately return 202 Accepted
        return '', 202
        
    except Exception as e:
        logger.error(f"Error receiving audio: {e}")
        logger.debug("Stack trace for receive_audio error:", exc_info=True)
        return jsonify({'error': str(e)}), 500
    

@app.route('/api/hello', methods=['GET'])
def hello_world():
    logger.debug("Received hello world request")
    return jsonify({'message': 'Hello, World!'}), 200


if __name__ == '__main__':
    logger.info("Starting Flask server on port 5000")
    app.run(port=5000)