# UAV Log Viewer

![log seeking](preview.gif "Logo Title Text 1")

 This is a Javascript based log viewer for Mavlink telemetry and dataflash logs.
 [Live demo here](http://plot.ardupilot.org).

## AI-Powered Chatbot Features

### Intelligent Flight Data Analysis
- **AI Assistant**: OpenAI-powered chatbot for natural language flight log analysis
- **Smart Queries**: Ask questions about flight data in plain English
- **Real-time Analysis**: Instant responses with contextual flight insights
- **Multi-interface Support**: Available in both sidebar and popup modes

### Key Chatbot Features
- **Flight Data Insights**: Get comprehensive analysis of flight logs, performance metrics, and anomaly detection
- **Natural Conversations**: Chat interface with typing animations and session memory
- **Dark Theme**: Modern UI optimized for extended analysis sessions
- **Responsive Design**: Seamless experience across sidebar and popup interfaces
- **State Synchronization**: Messages sync between sidebar and popup views
- **Real-time Processing**: Fast response times with loading indicators

### Usage Examples
Ask the AI assistant questions like:
- "What was the maximum altitude during this flight?"
- "Were there any GPS signal issues?"
- "Analyze the battery performance throughout the flight"
- "Show me any unusual vibration patterns"
- "What was the average ground speed?"

### Technical Implementation
- **Frontend**: Vue.js components with Bootstrap Vue styling
- **Backend**: FastAPI with OpenAI integration
- **Real-time Communication**: RESTful API with session management
- **Data Processing**: Comprehensive MAVLink log analysis
- **Error Handling**: Graceful error states with user-friendly messages

## Build Setup

``` bash
# install dependencies
npm install

# serve with hot reload at localhost:8080
npm run dev

# build for production with minification
npm run build

# run unit tests
npm run unit

# run e2e tests
npm run e2e

# run all tests
npm test
```

## Environment Configuration

For AI chatbot functionality, ensure the backend is running with proper OpenAI API configuration:

``` bash
# Backend setup (in backend directory)
pip install -r requirements.txt

# Set OpenAI API key
export OPENAI_API_KEY=your_api_key_here

# Run backend server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

# Docker

run the prebuilt docker image:

``` bash
docker run -p 8080:8080 -d ghcr.io/ardupilot/uavlogviewer:latest

```

or build the docker file locally:

``` bash

# Build Docker Image
docker build -t <your username>/uavlogviewer .

# Run Docker Image
docker run -e VUE_APP_CESIUM_TOKEN=<Your cesium ion token> -it -p 8080:8080 -v ${PWD}:/usr/src/app <your username>/uavlogviewer

# Navigate to localhost:8080 in your web browser

# changes should automatically be applied to the viewer

```
