# Real-Time Meeting Transcript Processor with Action Item Extraction

This example demonstrates how to receive and process incoming transcript data from a Zoom meeting using the RTMS (Real-Time Media Streaming) service, combined with LangChain and Claude to automatically extract action items from the conversation.

## Prerequisites

- Python 3.7 or higher
- A Zoom account with RTMS enabled
- Zoom App credentials (Client ID and Client Secret)
- Zoom Secret Token for webhook validation
- Anthropic API key for Claude access

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file in the same directory with your credentials:
```
ZOOM_SECRET_TOKEN=your_secret_token
ZM_CLIENT_ID=your_client_id
ZM_CLIENT_SECRET=your_client_secret
ANTHROPIC_API_KEY=your_anthropic_api_key
```

## Running the Example

1. Start the server:
```bash
python print_transcripts.py
```

2. The server will start on port 3000. You'll need to expose this port to the internet using a tool like ngrok:
```bash
ngrok http 3000
```

3. Configure your Zoom App's webhook URL to point to your exposed endpoint (e.g., `https://your-ngrok-url/webhook`)

4. Start a Zoom meeting and enable RTMS. The server will:
   - Receive and process the incoming transcript data
   - Extract action items using Claude
   - Print both the raw transcripts and identified action items to the console

## How it Works

The application is split into two main components:

### 1. Zoom RTMS Handler (`print_transcripts.py`)
- Listens for webhook events from Zoom
- Establishes WebSocket connections to Zoom's signaling and media servers
- Receives real-time transcript data
- Forwards transcript chunks to the LangChain processor

### 2. LangChain Processor (`langchain_processor.py`)
- Processes incoming transcript chunks
- Uses Claude (via LangChain) to analyze conversation context
- Extracts explicit and implicit action items
- Maintains a running list of unique action items
- Handles deduplication and context management

## Features

- Real-time transcript processing
- Automatic action item extraction
- Context-aware processing (maintains recent conversation history)
- Deduplication of action items
- Robust WebSocket connection handling
- Automatic keep-alive message handling

## Notes

- The system maintains a rolling window of recent transcript chunks to provide better context for action item extraction
- Action items are extracted based on both explicit and implicit mentions in the conversation
- The LangChain processor uses Claude 3 Sonnet for high-quality action item extraction
- In a production environment, you might want to add persistence for the extracted action items
- The system automatically handles WebSocket reconnections and keep-alive messages 