# Opus Converter

Opus Converter is a Flask-based server application that converts Opus audio files to WAV format. It provides an API endpoint for receiving Opus audio data and processes it in the background, saving the converted WAV files.

## Features

- Converts Opus audio to WAV format
- Asynchronous processing using a background worker
- Supports both user and AI audio inputs
- Saves converted audio files with timestamps

## Requirements

- Python 3.8 or higher
- Poetry for dependency management

## Installation

1. Clone the repository:

   ```
   git clone https://github.com/yourusername/opus-converter.git
   cd opus-converter
   ```

2. Install dependencies using Poetry:
   ```
   poetry install
   ```

## Usage

1. Start the server:

   ```
   poetry run python run.py
   ```

   The server will start on `http://0.0.0.0:3001` in debug mode.

2. Send Opus audio data to the `/api/audio` endpoint:

   - Use POST method
   - Set Content-Type header to `audio/opus`
   - Set X-Audio-Type header to `user` or `ai` to specify the audio source
   - Send the Opus audio data in the request body

3. The server will respond with a 202 Accepted status if the request is valid.

4. Converted WAV files will be saved in the `recordings` directory with timestamps and prefixes indicating the audio source (user or AI).

## API Endpoints

- POST `/api/audio`: Receive Opus audio data for conversion
- GET `/api/hello`: A simple "Hello, World!" endpoint for testing

## Project Structure

- `run.py`: Entry point for running the server
- `opus_converter/server.py`: Main server logic and API endpoints
- `opus_converter/__init__.py`: Package initialization
- `pyproject.toml`: Poetry configuration and dependencies
