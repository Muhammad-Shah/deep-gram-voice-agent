import asyncio
import logging
import os
import json
from typing import Dict, Optional, Union
import deepgram
import deepgram.clients
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn
from dotenv import load_dotenv
from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions,
    Microphone,
    SpeakOptions,
    TextSource,
)
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Initialize FastAPI app
app = FastAPI()

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/")
async def root():
    return FileResponse("app/static/index.html")

# Initialize Deepgram client
config: DeepgramClientOptions = DeepgramClientOptions(
    verbose=logging.DEBUG,
    api_key=os.getenv("DEEPGRAM_API_KEY"),  # Replace with your Deepgram API key
)

dg_client = DeepgramClient(config)

# Deepgram STT options
options: LiveOptions = LiveOptions(
    model="nova-2",
    language="en-US",
    punctuate=True,
    encoding="linear16",  # Adjust if using a different encoding from your client
    channels=1,
    sample_rate=16000,  # Update to match your client's sample rate
    # Add other options as needed
)

# Deepgram TTS options
tts_options: SpeakOptions = SpeakOptions(
    model="aura-asteria-en"
    # Add other TTS options as needed
)

# Example NLU (replace with your actual NLU implementation)
def process_text_with_nlu(transcript: str) -> Dict:
    """
    Placeholder for your NLU processing logic.
    Replace this with your actual NLU implementation (e.g., using an external NLU service).
    """
    # This is a very basic example:
    if "hello" in transcript.lower():
        return {"intent": "greeting", "response": "Hello, how can I help you?"}
    elif "goodbye" in transcript.lower():
        return {"intent": "farewell", "response": "Goodbye!"}
    else:
        return {"intent": "unknown", "response": "I didn't understand that."}

# Example Dialog Manager (replace with your actual implementation)
class DialogManager:
    def __init__(self):
        self.state = {}  # You might use a more sophisticated state management system

    def process_intent(self, intent_data: Dict) -> str:
        """
        Simple dialog manager that returns a response based on the intent.
        """
        intent = intent_data.get("intent")
        if intent == "greeting":
            return intent_data.get("response")
        elif intent == "farewell":
            return intent_data.get("response")
        else:
            return intent_data.get("response")

dialog_manager = DialogManager()

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket connection handler for the voicebot.
    """
    await websocket.accept()
    deepgram_socket = None
    try:
        # Create a new connection for each WebSocket connection
        deepgram_socket = dg_client.listen.websocket.v("1")

        async def on_message(self, result, **kwargs):
            """
            Callback function to handle messages received from Deepgram.
            """
            try:
                print(result)
                data = result.channel.alternatives[0]
                transcript = data.transcript
                if len(transcript) > 0:
                    # print for testing
                    print(f"transcript: {transcript}")

                    # Call NLU to get intent and entities
                    intent_data = process_text_with_nlu(transcript)
                    print(intent_data)

                    # Get response from Dialog Manager
                    response_text = dialog_manager.process_intent(intent_data)

                    # Call Deepgram TTS and send audio
                    payload: TextSource = {
                        "buffer": bytes(response_text, "utf-8"),
                    }

                    print(payload)

                    # Call the synchronous Deepgram client
                    res = deepgram.clients.speak.v("1").stream_request(
                        payload, tts_options
                    )
                    # check if no errors
                    if res:
                        # Send streaming audio to the client
                        await websocket.send_bytes(res["buffer"])
            except Exception as e:
                logging.error(f"Error in on_message callback: {e}")

        async def on_metadata(self, metadata, **kwargs):
            """
            Callback function to handle metadata received from Deepgram.
            """
            print(f"\n\n{metadata}\n\n")

        async def on_speech_started(self, speech_started, **kwargs):
            """
            Callback function to handle speech start events from Deepgram.
            """
            print(f"\n\n{speech_started}\n\n")

        async def on_utterance_end(self, utterance_end, **kwargs):
            """
            Callback function to handle utterance end events from Deepgram.
            """
            print(f"\n\n{utterance_end}\n\n")

        async def on_error(self, error, **kwargs):
            """
            Callback function to handle errors received from Deepgram.
            """
            print(f"\n\n{error}\n\n")

        # connect to websocket
        dg_connection = deepgram.clients.listen.websocket.v("1")
        dg_connection = deepgram.clients.listen.v1.

        # Connect to Deepgram
        try:
            dg_connection.start(
                options=options,
                on_open=on_message,
                on_message=on_message,
                on_metadata=on_metadata,
                on_speech_started=on_speech_started,
                on_utterance_end=on_utterance_end,
                on_error=on_error,
            )

        except Exception as e:
            print(f"Could not start connection: {e}")

        # Handle incoming messages from the client
        while True:
            data = await websocket.receive_bytes()

            # Send data through a new stream
            dg_connection.send(data)

    except WebSocketDisconnect:
        logging.info("WebSocket disconnected")
    except Exception as e:
        logging.error(f"Exception in websocket_endpoint: {e}")
    finally:
        # Ensure the Deepgram connection is closed on disconnect
        if dg_connection:
            dg_connection.finish()

# # Run the server using uvicorn (you might need to install it: pip install uvicorn)
# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8000)