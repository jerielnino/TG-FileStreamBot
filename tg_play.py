import os
import logging
from quart import Quart, Response, abort
from pyrogram import Client

# ==========================================
# CONFIGURATION
# ==========================================
# Replace these default values with your actual details
API_ID = int(os.environ.get("API_ID", 33433044)) 
API_HASH = os.environ.get("API_HASH", "004b07359a56a200099594631dd125d7")

# Put your integer Channel ID here (usually starts with -100)
CHANNEL_ID = int(os.environ.get("CHANNEL_ID", -1003726584253)) 

SERVER_IP = os.environ.get("SERVER_IP", "192.168.20.50")
SERVER_PORT = int(os.environ.get("SERVER_PORT", 5000))
SESSION_NAME = "myaccount"

# ==========================================
# INITIALIZATION
# ==========================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Quart(__name__)
tg = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH)

# ==========================================
# HELPER FUNCTIONS
# ==========================================
def get_media_name(msg) -> str:
    """Safely extracts a filename from a Pyrogram message."""
    if msg.video:
        return getattr(msg.video, 'file_name', None) or f"Video_{msg.id}.mp4"
    if msg.document:
        return getattr(msg.document, 'file_name', None) or f"Document_{msg.id}"
    return f"File_{msg.id}"

# ==========================================
# LIFECYCLE HOOKS
# ==========================================
@app.before_serving
async def startup():
    """Starts the Pyrogram client safely within the Quart event loop."""
    logger.info("Starting Telegram client...")
    await tg.start()
    # --- ADD THIS TEMPORARILY ---
    logger.info("Fetching dialogs to update peer cache...")
    async for dialog in tg.get_dialogs():
        pass 
    # ----------------------------
    logger.info("Telegram client started successfully.")

@app.after_serving
async def cleanup():
    """Stops the Pyrogram client gracefully when the server shuts down."""
    logger.info("Stopping Telegram client...")
    await tg.stop()

# ==========================================
# ROUTES
# ==========================================
@app.route("/playlist.m3u")
async def playlist():
    """Generates an M3U playlist from the channel's history."""
    lines = ["#EXTM3U"]
    
    try:
        # Using CHANNEL_ID here
        async for msg in tg.get_chat_history(CHANNEL_ID, limit=200):
            if msg.video or msg.document:
                name = get_media_name(msg)
                stream_url = f"http://{SERVER_IP}:{SERVER_PORT}/stream/{msg.id}"
                
                lines.append(f"#EXTINF:-1,{name}")
                lines.append(stream_url)
                
    except Exception as e:
        logger.error(f"Failed to generate playlist: {e}")
        return Response("Internal Server Error fetching playlist", status=500)

    return Response("\n".join(lines) + "\n", mimetype="audio/x-mpegurl")


@app.route("/stream/<int:msg_id>")
async def stream(msg_id):
    """Streams the media of a specific Telegram message."""
    try:
        # Using CHANNEL_ID here
        msg = await tg.get_messages(CHANNEL_ID, msg_id)
        
        # Check if message exists and actually contains media
        if not msg or not (msg.video or msg.document):
            abort(404, description="Media not found or invalid message type.")

        async def generate():
            async for chunk in tg.stream_media(msg):
                yield chunk

        return Response(generate(), content_type="application/octet-stream")
        
    except Exception as e:
        logger.error(f"Failed to stream message {msg_id}: {e}")
        abort(500, description="Internal Server Error while streaming")

# ==========================================
# MAIN RUNNER
# ==========================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=SERVER_PORT)
