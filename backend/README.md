# UAV Chatbot Backend

FastAPI backend for analyzing UAV flight telemetry data with OpenAI-powered chatbot.

## Features

- **MAVLink Parser**: Analyze .bin flight log files
- **AI Chatbot**: OpenAI-powered flight data analysis
- **RESTful API**: FastAPI with automatic documentation
- **Flight Data Queries**: Altitude, GPS, battery, errors, duration analysis

## Setup

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 2. Configure OpenAI API

```bash
# Copy example environment file
cp .env.example .env

# Edit .env file and add your OpenAI API key
# OPENAI_API_KEY=your_actual_openai_api_key_here
```

### 3. Run Server

```bash
# Start the backend server
uvicorn main:app --reload --port 8001

# Server will be available at:
# http://localhost:8001
# API docs at: http://localhost:8001/docs
```

## API Endpoints

- `POST /chat` - Chat with AI about flight data
- `POST /upload-flight-log` - Upload .bin flight logs
- `GET /flight-summary` - Get flight data summary
- `POST /query-flight-data` - Query specific flight metrics

## Usage

1. Start the backend server
2. Open the frontend Vue.js application
3. Upload a .bin flight log file
4. Use the chatbot to ask questions about your flight data

## Example Queries

- "What was the maximum altitude?"
- "How long was the flight?"
- "Were there any GPS issues?"
- "Show me battery temperature data"
- "Were there any critical errors?"

## Models Supported

- `gpt-3.5-turbo` (default)
- `gpt-4`
- `gpt-3.5-turbo-16k`

Configure in `.env` file: `OPENAI_MODEL=gpt-4` 