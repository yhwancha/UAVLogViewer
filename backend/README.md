# UAV Flight Log Analyzer - Backend

FastAPI backend for analyzing UAV flight telemetry data with AI-powered chatbot capabilities.

## Features

### 🚁 MAVLink Processing
- **Flight Log Parser**: Comprehensive .bin flight log file analysis
- **Real-time Data Processing**: Asynchronous MAVLink message parsing
- **Flight Statistics**: Automated calculation of key flight metrics
- **Data Validation**: Built-in error detection and data integrity checks

### 🤖 AI-Powered Analysis
- **Intelligent Chatbot**: OpenAI-powered flight data analysis
- **Natural Language Queries**: Ask questions in plain English
- **Contextual Responses**: Maintains conversation context and session state
- **Multi-model Support**: Configurable OpenAI model selection

### 📊 RESTful API
- **FastAPI Framework**: High-performance async API with automatic documentation
- **CORS Support**: Cross-origin resource sharing for frontend integration
- **File Uploads**: Secure .bin file handling with validation
- **Health Monitoring**: Built-in health check and debug endpoints

### 🔍 Flight Data Queries
- **Altitude Analysis**: Min/max/average altitude calculations
- **GPS Tracking**: Location data and waypoint analysis
- **Battery Monitoring**: Voltage, current, and temperature tracking
- **Error Detection**: Critical system alerts and warning analysis
- **Flight Duration**: Precise timing and duration calculations
- **Vehicle Information**: Aircraft type and configuration details

## Architecture

```
backend/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── chatbot/               # AI chatbot components
│   ├── agent.py           # Main chatbot logic and conversation handling
│   ├── llm_client.py      # OpenAI API client and model management
│   └── query_parser.py    # Natural language query processing
├── mavlink_parser/        # MAVLink data processing
│   └── parser.py          # Flight log parsing and analysis
└── models/               # Pydantic data models
    └── chat_models.py    # Request/response models
```

## Setup

### 1. Environment Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the backend directory:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_actual_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo  # or gpt-4, gpt-3.5-turbo-16k

# Server Configuration (Optional)
HOST=0.0.0.0
PORT=8001
LOG_LEVEL=INFO
```

### 3. Run Development Server

```bash
# Start the backend server with auto-reload
uvicorn main:app --reload --port 8001

# Server endpoints:
# - Main API: http://localhost:8001
# - Interactive docs: http://localhost:8001/docs
# - ReDoc: http://localhost:8001/redoc
```

## API Reference

### Core Endpoints

#### `POST /upload-flight-log`
Upload and parse MAVLink .bin flight log files.

**Request:**
- `file`: Binary flight log file (.bin format)

**Response:**
```json
{
  "message": "Flight log uploaded and parsed successfully",
  "flight_info": {
    "duration": "15m 32s",
    "duration_seconds": 932,
    "messages_count": 12845,
    "start_time": "2024-01-15T10:30:00Z",
    "vehicle_type": "Quadcopter",
    "max_altitude": 120.5,
    "summary": "Successful flight with normal operations..."
  }
}
```

#### `POST /chat`
Interactive chat with AI about flight data.

**Request:**
```json
{
  "content": "What was the maximum altitude during the flight?",
  "session_id": "unique-session-id"
}
```

**Response:**
```json
{
  "content": "The maximum altitude reached during this flight was 120.5 meters above the home position...",
  "message_type": "response",
  "data": {
    "altitude": 120.5,
    "timestamp": "2024-01-15T10:45:30Z"
  }
}
```

#### `GET /flight-summary`
Get comprehensive flight data summary.

#### `POST /query-flight-data`
Execute structured queries against flight data.

### Utility Endpoints

- `GET /` - Root endpoint status
- `GET /health` - Health check
- `GET /debug/flight-store` - Debug flight data storage

## Usage Examples

### Basic Workflow

1. **Start the server**
   ```bash
   uvicorn main:app --reload --port 8001
   ```

2. **Upload flight log** (via frontend or API client)
   ```bash
   curl -X POST "http://localhost:8001/upload-flight-log" \
        -H "accept: application/json" \
        -H "Content-Type: multipart/form-data" \
        -F "file=@flight_log.bin"
   ```

3. **Chat about your flight data**
   ```bash
   curl -X POST "http://localhost:8001/chat" \
        -H "Content-Type: application/json" \
        -d '{"content": "How long was the flight?", "session_id": "session1"}'
   ```

### Example Queries

#### Flight Performance
- "What was the maximum altitude?"
- "How long was the flight?"
- "What was the average ground speed?"
- "Show me the flight path"

#### System Health
- "Were there any GPS issues?"
- "Check battery temperature during flight"
- "Were there any critical errors or warnings?"
- "How was the compass calibration?"

#### Data Analysis
- "Compare altitude vs battery voltage"
- "Show me vibration levels throughout the flight"
- "What was the wind speed during takeoff?"
- "Analyze power consumption patterns"

## Supported Models

### OpenAI Models
- `gpt-3.5-turbo` (default) - Fast, cost-effective
- `gpt-4` - More accurate, detailed analysis
- `gpt-3.5-turbo-16k` - Extended context for large datasets

Configure in `.env` file:
```bash
OPENAI_MODEL=gpt-4
```

## Development

### Adding New Features

1. **New API Endpoints**: Add to `main.py`
2. **Chat Capabilities**: Extend `chatbot/agent.py`
3. **Data Models**: Define in `models/chat_models.py`
4. **MAVLink Features**: Enhance `mavlink_parser/parser.py`

### Testing

```bash
# Run test server
python test_server.py

# Access interactive API documentation
# http://localhost:8001/docs
```

### Logging

The application uses Python's built-in logging:
- **INFO**: Normal operations and request processing
- **WARNING**: Non-critical issues and validation errors
- **ERROR**: Exceptions and critical failures

Logs include:
- File upload processing
- MAVLink parsing status
- Chat message handling
- API request/response cycles

## Dependencies

### Core Libraries
- **FastAPI**: Modern web framework for APIs
- **Uvicorn**: ASGI server for high performance
- **OpenAI**: Official OpenAI API client
- **PyMAVLink**: MAVLink protocol implementation

### Data Processing
- **Pandas**: Data analysis and manipulation
- **NumPy**: Numerical computing
- **Pydantic**: Data validation and serialization

### Additional
- **HTTPX**: Async HTTP client
- **WebSockets**: Real-time communication support
- **LXML**: XML processing for configuration files

## Production Considerations

- Configure proper CORS origins instead of `allow_origins=["*"]`
- Use environment-specific configuration files
- Implement persistent data storage (database)
- Add authentication and authorization
- Set up monitoring and logging aggregation
- Consider rate limiting for API endpoints
- Use HTTPS in production deployment 