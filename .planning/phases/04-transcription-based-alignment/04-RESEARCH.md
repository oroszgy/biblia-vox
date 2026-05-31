# Phase 4 Technical Research

## Architecture

1. **Dockerized Alignment Services**: The Python app (host) invokes Docker containers to execute model inference via `docker-compose run`. The containers share `./data` volume.
2. **Model Gauntlet**: `config.py` contains a list of models to evaluate. The script dynamically loads them.
3. **VibeVoice Exploration**: VibeVoice uses the Vibe model. It can be integrated as another transcription backend in the gauntlet.
4. **Fuzzy Matching**: Word-level RapidFuzz against transcriptions.

## Dependencies
- `faster-whisper`
- `rapidfuzz`

