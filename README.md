# UAV Log Viewer

![log seeking](preview.gif "UAV Log Viewer Demo")

A modern JavaScript-based log viewer for MAVLink telemetry and dataflash logs with **AI-powered flight data analysis**. 
[Live demo here](http://plot.ardupilot.org).

## 🚁 Features

### Core Functionality
- **Multi-format Support**: MAVLink telemetry logs (.tlog), dataflash logs (.bin), and DJI logs
- **Interactive 3D Visualization**: Cesium-powered 3D flight path visualization
- **Advanced Plotting**: Plotly.js-based charts with multiple data series
- **Real-time Analysis**: Live data streaming and analysis capabilities
- **Expression Editor**: Custom mathematical expressions for data analysis

### 🤖 AI-Powered Chatbot Features

#### Intelligent Flight Data Analysis
- **Natural Language Interface**: Ask questions about flight data in plain English
- **Comprehensive Analysis**: Automatic flight pattern detection and anomaly identification
- **Multi-Modal Interface**: Available in both sidebar and draggable popup modes
- **Chain-of-Thought Reasoning**: Advanced AI reasoning for complex flight analysis
- **Smart Clarifications**: AI-generated follow-up questions for ambiguous queries

#### Key Chatbot Capabilities
- **Flight Performance Analysis**: Battery performance, altitude patterns, GPS signal quality
- **Anomaly Detection**: Automatic identification of unusual flight patterns and issues
- **Telemetry Insights**: Detailed analysis of sensor data and flight parameters
- **Conversational Memory**: Session-based conversation history and context
- **Real-time Processing**: Fast responses with typing animations and loading indicators
- **Formatted Responses**: Rich text formatting with bold highlights and bullet points

#### Usage Examples
Ask the AI assistant questions like:
- *"What was the maximum altitude during this flight?"*
- *"Were there any GPS signal issues?"*
- *"Analyze the battery performance throughout the flight"*
- *"Detect any anomalies or unusual patterns in this flight"*
- *"How did the vibration levels affect flight stability?"*
- *"What was the flight duration and average ground speed?"*

## 🏗️ Architecture

### Frontend (Vue.js)
- **Framework**: Vue.js 2.7 with Vue Router
- **UI Components**: Bootstrap Vue with custom styling
- **3D Visualization**: Cesium for interactive 3D flight paths
- **Charting**: Plotly.js for advanced data visualization
- **State Management**: Vuex-like pattern with component-based state

### Backend (Python FastAPI)
- **API Framework**: FastAPI with async/await support
- **AI Integration**: OpenAI GPT models for natural language processing
- **Data Processing**: MAVLink parser with pandas for data analysis
- **File Handling**: Support for .bin, .tlog, and other flight log formats
- **Session Management**: Redis-based session storage for conversation history

### Key Components
- **`ChatbotPopup.vue`**: Draggable popup chatbot interface
- **`SideBarMessageMenu.vue`**: Integrated sidebar chat interface
- **`CesiumViewer.vue`**: 3D flight visualization component
- **`Plotly.vue`**: Advanced plotting and data analysis
- **`agent_manager.py`**: AI chatbot logic and conversation handling
- **`mavlink_parser/`**: Flight log parsing and data extraction

## 🚀 Quick Start

### Prerequisites
- **Node.js** >= 16.0.0
- **Python** >= 3.8
- **OpenAI API Key** (for AI chatbot functionality)

### Frontend Setup
```bash
# Clone the repository
git clone https://github.com/ArduPilot/UAVLogViewer.git
cd UAVLogViewer

# Install dependencies
npm install

# Start development server
npm run dev
# Frontend will be available at http://localhost:8080
```

### Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY=your_openai_api_key_here

# Start backend server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
# Backend API will be available at http://localhost:8000
```

### Environment Configuration

#### Backend Environment (.env)
Create a `.env` file in the `backend/` directory:

```env
# OpenAI Configuration (Required for AI Chatbot)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=1000
OPENAI_TEMPERATURE=0.7

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=INFO

# CORS Configuration
CORS_ORIGINS=["http://localhost:8080", "http://127.0.0.1:8080"]
CORS_ALLOW_CREDENTIALS=true

# Session Management
SESSION_SECRET_KEY=your_secret_key_here
SESSION_EXPIRE_SECONDS=3600

# File Upload Configuration
MAX_UPLOAD_SIZE=100MB
UPLOAD_TIMEOUT=300
ALLOWED_FILE_TYPES=[".bin", ".tlog", ".log"]

# MAVLink Parser Configuration
MAVLINK_TIMEOUT=30
MAVLINK_BUFFER_SIZE=8192
ENABLE_MESSAGE_VALIDATION=true

# Redis Configuration (Optional - for session storage)
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=
REDIS_DB=0

# Logging Configuration
LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
LOG_FILE=logs/uavlogviewer.log
ENABLE_FILE_LOGGING=false
```

#### Frontend Environment (.env)
Create a `.env` file in the project root directory:

```env
# Vue.js Development Configuration
NODE_ENV=development
VUE_APP_BASE_URL=http://localhost:8080

# Backend API Configuration
VUE_APP_API_BASE_URL=http://localhost:8000
VUE_APP_API_TIMEOUT=30000

# Cesium Configuration (Required for 3D visualization)
VUE_APP_CESIUM_TOKEN=your_cesium_ion_access_token_here
VUE_APP_CESIUM_TERRAIN_URL=https://world-terrain.cesium.com
VUE_APP_CESIUM_ION_URL=https://api.cesium.com

# Map Configuration
VUE_APP_DEFAULT_MAP_PROVIDER=cesium
VUE_APP_ENABLE_TERRAIN=true
VUE_APP_DEFAULT_CAMERA_HEIGHT=1000

# Chatbot Configuration
VUE_APP_ENABLE_CHATBOT=true
VUE_APP_CHATBOT_MAX_MESSAGES=50
VUE_APP_CHATBOT_TYPING_SPEED=50
VUE_APP_ENABLE_POPUP_CHATBOT=true

# File Upload Configuration
VUE_APP_MAX_FILE_SIZE=104857600
VUE_APP_SUPPORTED_FORMATS=".bin,.tlog,.log"
VUE_APP_UPLOAD_TIMEOUT=300000

# Performance Configuration
VUE_APP_ENABLE_PERFORMANCE_MONITORING=false
VUE_APP_MAX_DATA_POINTS=10000
VUE_APP_CHART_ANIMATION=true

# Debug Configuration
VUE_APP_DEBUG=false
VUE_APP_ENABLE_CONSOLE_LOGS=false
VUE_APP_SENTRY_DSN=

# Feature Flags
VUE_APP_ENABLE_EXPERIMENTAL_FEATURES=false
VUE_APP_ENABLE_OFFLINE_MODE=false
```

#### Production Environment Variables

For production deployment, use these additional configurations:

**Backend Production (.env.production):**
```env
# Production overrides
DEBUG=false
LOG_LEVEL=WARNING
HOST=0.0.0.0
PORT=8000

# Security
CORS_ORIGINS=["https://your-domain.com"]
SESSION_SECRET_KEY=your_production_secret_key_here

# Performance
OPENAI_MAX_TOKENS=800
MAVLINK_BUFFER_SIZE=16384

# Monitoring
ENABLE_FILE_LOGGING=true
LOG_FILE=/var/log/uavlogviewer/app.log
```

**Frontend Production (.env.production):**
```env
# Production overrides
NODE_ENV=production
VUE_APP_BASE_URL=https://your-domain.com
VUE_APP_API_BASE_URL=https://api.your-domain.com

# Performance optimizations
VUE_APP_CHART_ANIMATION=false
VUE_APP_MAX_DATA_POINTS=5000
VUE_APP_ENABLE_PERFORMANCE_MONITORING=true

# Security
VUE_APP_DEBUG=false
VUE_APP_ENABLE_CONSOLE_LOGS=false
```

#### Required API Keys

1. **OpenAI API Key** (Required for AI chatbot):
   - Sign up at [OpenAI Platform](https://platform.openai.com/)
   - Create API key in your dashboard
   - Add to `OPENAI_API_KEY` in backend `.env`

2. **Cesium Ion Access Token** (Required for 3D maps):
   - Sign up at [Cesium Ion](https://cesium.com/ion/)
   - Create access token in your dashboard
   - Add to `VUE_APP_CESIUM_TOKEN` in frontend `.env`

#### Docker Environment Configuration

For Docker deployment, create a `.env` file in the project root:

```env
# Docker Compose Configuration
COMPOSE_PROJECT_NAME=uavlogviewer

# Backend Service
BACKEND_PORT=8000
BACKEND_HOST=backend

# Frontend Service  
FRONTEND_PORT=8080
FRONTEND_HOST=frontend

# Volumes
LOG_VOLUME=./logs
DATA_VOLUME=./data

# Network
NETWORK_NAME=uavlogviewer_network

# Environment
ENVIRONMENT=production
```

## 📦 Build & Deployment

### Production Build
```bash
# Build frontend for production
npm run build

# Build backend Docker image
cd backend
docker build -t uavlogviewer-backend .

# Build frontend Docker image
cd ..
docker build -t uavlogviewer-frontend .
```

### Docker Deployment

After Environment Configuration

```bash
# Run with Docker Compose
docker-compose up -d --build

# Or run individual containers
docker run -p 8080:8080 -d ghcr.io/ardupilot/uavlogviewer:latest
```

### Manual Docker Build
```bash
# Build Docker Image
docker build -t <your-username>/uavlogviewer .

# Run with environment variables
docker run \
  -e VUE_APP_CESIUM_TOKEN=<your-cesium-token> \
  -e OPENAI_API_KEY=<your-openai-key> \
  -it -p 8080:8080 \
  -v ${PWD}:/usr/src/app \
  <your-username>/uavlogviewer
```

## 🧪 Testing

### Test Scripts
The project includes comprehensive test scripts for the AI chatbot functionality:

```bash
# Test upload endpoint
python test_upload_endpoint.py

# Test complete workflow (upload + chatbot)
python test_chatbot_interaction.py

# Test with your own flight log
python test_chatbot_interaction.py /path/to/your/flight.bin
```

### Unit & Integration Tests
```bash
# Run unit tests
npm run unit

# Run end-to-end tests
npm run e2e

# Run all tests
npm test

# Lint code
npm run lint
```

## 🔧 Development

### Available Scripts
```bash
npm run dev          # Development server with hot reload
npm run build        # Production build
npm run test         # Run all tests
npm run lint         # Lint and fix code
npm run lint:fix     # Auto-fix linting issues
```

### Project Structure
```
UAVLogViewer/
├── src/                    # Frontend source code
│   ├── components/         # Vue components
│   │   ├── ChatbotPopup.vue
│   │   ├── SideBarMessageMenu.vue
│   │   └── CesiumViewer.vue
│   ├── router/            # Vue Router configuration
│   └── assets/            # Static assets
├── backend/               # Python backend
│   ├── agent/            # AI chatbot logic
│       ├── prompts/      # AI prompt templates
│   ├── llm/              # OpenAI client
│   ├── mavlink_parser/   # Flight log parsing
│   └── main.py           # FastAPI application
├── test/                 # Test files
├── build/                # Build configuration
└── docker-compose.yml    # Docker deployment
```

## 🎯 AI Chatbot Features Detail

### Conversation Types
1. **Flight Data Analysis**: Comprehensive flight log analysis with telemetry insights
2. **Anomaly Detection**: Pattern recognition and issue identification
3. **Performance Metrics**: Battery, GPS, altitude, and speed analysis
4. **General Knowledge**: UAV and flight-related technical questions
5. **Clarification Requests**: Smart follow-up questions for ambiguous queries

### Response Features
- **Word Limit Control**: Concise responses (80-100 words) with auto-summarization
- **Rich Formatting**: Bold text, bullet points, and structured information
- **Chain-of-Thought**: Hidden reasoning process for complex analysis
- **Session Memory**: Conversation context and history maintenance
- **Error Handling**: Graceful error states with helpful suggestions

### Supported File Formats
- **ArduPilot Logs**: .bin dataflash logs with full MAVLink message support
- **Telemetry Logs**: .tlog files with real-time data streams
- **DJI Logs**: Native DJI flight log format support
- **Custom Formats**: Extensible parser architecture

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Guidelines
- Follow Vue.js and Python best practices
- Add tests for new features
- Update documentation for API changes
- Use ESLint for JavaScript code formatting
- Follow PEP 8 for Python code style

## 📄 License

This project is licensed under the GPL-3.0 License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **ArduPilot Community**: For the foundational flight control software
- **Cesium**: For 3D visualization capabilities
- **OpenAI**: For AI-powered natural language processing
- **Vue.js & FastAPI**: For modern web framework foundations

## 📞 Support

- **Documentation**: [ArduPilot Documentation](https://ardupilot.org/dev/)
- **Community Forum**: [ArduPilot Discuss](https://discuss.ardupilot.org/)
- **Issues**: [GitHub Issues](https://github.com/ArduPilot/UAVLogViewer/issues)
- **Live Demo**: [plot.ardupilot.org](http://plot.ardupilot.org)
