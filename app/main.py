from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from dotenv import load_dotenv
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions, SpeakOptions
from deepgram.audio import Microphone, Speaker
from openai import AsyncOpenAI
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

# Initialize clients
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not DEEPGRAM_API_KEY or not OPENAI_API_KEY:
    raise ValueError("API keys not set in environment variables")

deepgram = DeepgramClient(DEEPGRAM_API_KEY)
openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def generate_response(user_input: str) -> str:
    """Generate response using OpenAI"""
    response = await openai_client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=[
            {"role": "system", "content": "You are a helpful voice assistant. Keep responses concise and conversational."},
            {"role": "user", "content": user_input}
        ]
    )
    return response.choices[0].message.content

async def text_to_speech(text: str) -> bytes:
    """Convert text to speech using Deepgram"""
    options = SpeakOptions(model="aura-asteria-en")
    response = await deepgram.speak.rest.v("1").stream({"text": text}, options)
    return response

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Create Deepgram live transcription connection
    dg_connection = deepgram.listen.websocket.v("1")
    
    async def on_message(result):
        try:
            transcript = result.channel.alternatives[0].transcript
            if transcript.strip():
                # Get AI response
                ai_response = await generate_response(transcript)
                logger.info(f"User: {transcript}")
                logger.info(f"AI: {ai_response}")
                
                # Convert AI response to speech
                audio_data = await text_to_speech(ai_response)
                
                # Send both text and audio back to client
                await websocket.send_json({
                    "type": "response",
                    "text": ai_response,
                    "audio": audio_data.decode('utf-8')
                })
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    # Set up Deepgram live transcription
    dg_connection.on(LiveTranscriptionEvents.Transcript, on_message)
    
    try:
        # Start Deepgram connection
        options = LiveOptions(model="nova-2")
        await dg_connection.start(options)
        
        # Handle incoming WebSocket messages
        while True:
            data = await websocket.receive_bytes()
            await dg_connection.send(data)
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await dg_connection.finish()
    