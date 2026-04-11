#!/usr/bin/env bash

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama in background
ollama serve &

# Give it time to start
sleep 5

# Pull small model
ollama pull tinyllama

# Start API
uvicorn app:app --host 0.0.0.0 --port $PORT