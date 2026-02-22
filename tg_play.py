import os
import re
import logging
from urllib.parse import quote
from quart import Quart, Response, abort, request
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
    if msg.video:
        return getattr(msg.video, 'file_name', None) or f"Video_{msg.id}.mp4"
    if msg.document:
        return getattr(msg.document, 'file_name', None) or f"Document_{msg.id}"
    return f"File_{msg.id}.mp4"

def get_mime_type(msg) -> str:
    if msg.video and msg.video.mime_type:
        return msg.video.mime_type
    if msg.document and msg.document.mime_type:
        return msg.document.mime_type
    return "video/mp4"

# ==========================================
# LIFECYCLE HOOKS
# ==========================================
@app.before_serving
async def startup():
    logger.info("Starting Telegram client...")
    await tg.start()
    logger.info("Telegram client started successfully.")

@app.after_serving
async def cleanup():
    logger.info("Stopping Telegram client...")
    await tg.stop()

# ==========================================
# ROUTES
# ==========================================
@app.route("/playlist.m3u")
async def playlist():
    lines = ["#EXTM3U"]
    try:
        async for msg in tg.get_chat_history(CHANNEL_ID, limit=200):
            if msg.video or msg.document:
                name = get_media_name(msg)
                safe_name = quote(name)
                
                # The links for both the video and the new thumbnail
                stream_url = f"http://{SERVER_IP}:{SERVER_PORT}/stream/{msg.id}/{safe_name}"
                thumb_url = f"http://{SERVER_IP}:{SERVER_PORT}/thumb/{msg.id}.jpg"
                
                # Added the tvg-logo attribute
                lines.append(f'#EXTINF:-1 tvg-type="movies" group-title="Telegram VOD" tvg-logo="{thumb_url}",{name}')
                lines.append(stream_url)

    except Exception as e:
        logger.error(f"Failed to generate playlist: {e}")
        return Response("Internal Server Error fetching playlist", status=500)

    return Response("\n".join(lines) + "\n", mimetype="audio/x-mpegurl")


# FIX: Updated route to accept the filename at the end
@app.route("/stream/<int:msg_id>/<filename>", methods=["GET", "HEAD"])
async def stream(msg_id, filename):
    try:
        msg = await tg.get_messages(CHANNEL_ID, msg_id)
        if not msg or not (msg.video or msg.document):
            abort(404, description="Media not found")

        file_size = msg.video.file_size if msg.video else msg.document.file_size
        mime_type = get_mime_type(msg)
        
        range_header = request.headers.get("Range")
        start = 0
        end = file_size - 1
        
        if range_header:
            match = re.search(r"bytes=(\d+)-(\d*)", range_header)
            if match:
                start = int(match.group(1))
                if match.group(2):
                    end = int(match.group(2))
                    
        length = end - start + 1
        status_code = 206 if range_header else 200

        # FIX 1: Answer ExoPlayer's 'HEAD' probe instantly without downloading video
        if request.method == "HEAD":
            response = Response(status=status_code, content_type=mime_type)
            response.headers.add("Accept-Ranges", "bytes")
            response.headers.add("Content-Length", str(length))
            if status_code == 206:
                response.headers.add("Content-Range", f"bytes {start}-{end}/{file_size}")
            return response

        # Actual video generation for GET requests
        async def generate():
            chunk_size = 1048576 
            offset_chunks = start // chunk_size
            skip_bytes = start % chunk_size
            bytes_yielded = 0
            
            try:
                async for chunk in tg.stream_media(msg, offset=offset_chunks):
                    if skip_bytes > 0:
                        chunk = chunk[skip_bytes:]
                        skip_bytes = 0
                        
                    if bytes_yielded + len(chunk) > length:
                        chunk = chunk[:length - bytes_yielded]
                        
                    yield chunk
                    bytes_yielded += len(chunk)
                    
                    if bytes_yielded >= length:
                        break
            except Exception:
                # Silently catch when TiviMate skips ahead and drops the old connection
                pass

        response = Response(generate(), status=status_code, content_type=mime_type)
        response.headers.add("Accept-Ranges", "bytes")
        response.headers.add("Content-Length", str(length))
        
        # FIX 2: Only send Content-Range on 206 Partial Content, never on 200 OK
        if status_code == 206:
            response.headers.add("Content-Range", f"bytes {start}-{end}/{file_size}")
            
        return response
        
    except Exception as e:
        logger.error(f"Failed to stream message {msg_id}: {e}")
        abort(500, description="Internal Server Error")

@app.route("/thumb/<int:msg_id>.jpg")
async def thumb(msg_id):
    try:
        msg = await tg.get_messages(CHANNEL_ID, msg_id)
        if not msg:
            abort(404)
        
        # Locate the thumbnail file_id if it exists
        thumb_file_id = None
        if msg.video and msg.video.thumbs:
            thumb_file_id = msg.video.thumbs[0].file_id
        elif msg.document and msg.document.thumbs:
            thumb_file_id = msg.document.thumbs[0].file_id
            
        if not thumb_file_id:
            # If the file has no thumbnail, return a 404 so TiviMate uses a placeholder
            abort(404, description="No thumbnail found")
            
        # Download the thumbnail directly to memory
        file_stream = await tg.download_media(thumb_file_id, in_memory=True)
        
        # Send the raw JPEG bytes to the media player
        return Response(file_stream.getvalue(), mimetype="image/jpeg")
        
    except Exception as e:
        logger.error(f"Failed to fetch thumb for message {msg_id}: {e}")
        abort(500)
      
# ==========================================
# MAIN RUNNER
# ==========================================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=SERVER_PORT)
