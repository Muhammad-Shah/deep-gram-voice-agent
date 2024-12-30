from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio
import json
import os
from dotenv import load_dotenv
from deepgram import DeepgramClient
from deepgram import DeepgramClientOptions
from deepgram import AgentWebSocketEvents
from deepgram import SettingsConfigurationOptions
from deepgram.utils import verboselogs
import logging

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Intelligent Voice Agent")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Initialize Deepgram client with configuration
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
if not DEEPGRAM_API_KEY:
    raise ValueError("DEEPGRAM_API_KEY environment variable is not set")

config = DeepgramClientOptions(
    options={
        "keepalive": "true",
        "microphone_record": "true",
        "speaker_playback": "true",
    },
)
deepgram = DeepgramClient(DEEPGRAM_API_KEY, config)

@app.get("/")
async def root():
    return {"message": "Intelligent Voice Agent API"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        # Create a websocket connection to Deepgram
        dg_connection = deepgram.agent.websocket.v("1")

        # Event handlers for Deepgram websocket events
        async def on_open(open_event, **kwargs):
            logger.info(f"Deepgram connection opened: {open_event}")
            await websocket.send_json({"type": "status", "message": "Connected to Deepgram"})

        async def on_binary_data(data, **kwargs):
            logger.debug("Received binary audio data")

        async def on_welcome(welcome, **kwargs):
            logger.info(f"Received welcome message: {welcome}")

        async def on_settings_applied(settings_applied, **kwargs):
            logger.info(f"Settings applied: {settings_applied}")

        async def on_conversation_text(conversation_text, **kwargs):
            logger.info(f"Conversation text: {conversation_text}")
            # Send both the user's text and the agent's response to the frontend
            await websocket.send_json({
                "type": "transcript",
                "text": conversation_text.get("user_message", ""),
                "response": conversation_text.get("agent_message", "")
            })

        async def on_user_started_speaking(user_started_speaking, **kwargs):
            logger.info("User started speaking")

        async def on_agent_thinking(agent_thinking, **kwargs):
            logger.info("Agent is thinking")

        async def on_agent_started_speaking(agent_started_speaking, **kwargs):
            logger.info("Agent started speaking")

        async def on_agent_audio_done(agent_audio_done, **kwargs):
            logger.info("Agent audio done")

        async def on_close(close_event, **kwargs):
            logger.info(f"Deepgram connection closed: {close_event}")

        async def on_error(error, **kwargs):
            logger.error(f"Deepgram error: {error}")
            await websocket.send_json({"type": "error", "message": str(error)})

        # Register event handlers
        dg_connection.on(AgentWebSocketEvents.Open, on_open)
        dg_connection.on(AgentWebSocketEvents.AudioData, on_binary_data)
        dg_connection.on(AgentWebSocketEvents.Welcome, on_welcome)
        dg_connection.on(AgentWebSocketEvents.SettingsApplied, on_settings_applied)
        dg_connection.on(AgentWebSocketEvents.ConversationText, on_conversation_text)
        dg_connection.on(AgentWebSocketEvents.UserStartedSpeaking, on_user_started_speaking)
        dg_connection.on(AgentWebSocketEvents.AgentThinking, on_agent_thinking)
        dg_connection.on(AgentWebSocketEvents.AgentStartedSpeaking, on_agent_started_speaking)
        dg_connection.on(AgentWebSocketEvents.AgentAudioDone, on_agent_audio_done)
        dg_connection.on(AgentWebSocketEvents.Close, on_close)
        dg_connection.on(AgentWebSocketEvents.Error, on_error)

        # Configure agent settings
        options = SettingsConfigurationOptions()
        options.agent.think.provider.type = "open_ai"
        options.agent.think.model = "gpt-4"
        options.agent.think.instructions = """You are an intelligent and helpful AI assistant capable of engaging in natural conversation. 
        You should be concise but informative, friendly but professional. 
        You can help with various tasks including answering questions, providing explanations, and engaging in casual conversation.
        Keep your responses relatively brief and conversational, as they will be spoken out loud."""

        # Start the Deepgram connection
        if not dg_connection.start(options):
            raise Exception("Failed to start Deepgram connection")

        # Main loop for receiving audio data
        while True:
            try:
                data = await websocket.receive_bytes()
                dg_connection.send(data)
            except Exception as e:
                logger.error(f"Error receiving audio data: {e}")
                break

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        try:
            await dg_connection.finish()
        except Exception as e:
            logger.error(f"Error closing Deepgram connection: {e}")
        
        try:
            await websocket.close()
        except Exception as e:
            logger.error(f"Error closing WebSocket: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
