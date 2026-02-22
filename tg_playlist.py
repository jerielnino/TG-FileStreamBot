from flask import Flask, Response
from pyrogram import Client
import asyncio

API_ID = 33433044
API_HASH = "004b07359a56a200099594631dd125d7"
BOT_TOKEN = "7905710256:AAGBSDX83F4ftuOKgSBxj981k0ET8N0eG5M"
CHANNEL_ID = -1003791091909
SERVER_IP = "192.168.20.50"  # your phone IP

app = Flask(__name__)

tg = Client(
    "myaccount",
    api_id=API_ID,
    api_hash=API_HASH
)

@app.route("/playlist.m3u")
def playlist():
    async def build():
        m3u = "#EXTM3U\n"
        async for msg in tg.get_chat_history(CHANNEL_ID, limit=100):
            if msg.video or msg.document:
                title = (
                    msg.video.file_name if msg.video
                    else msg.document.file_name
                ) or f"File {msg.id}"

                m3u += f"#EXTINF:-1,{title}\n"
                m3u += f"http://{SERVER_IP}:8080/stream/{msg.id}\n"
        return m3u

    return asyncio.run(build())

@app.route("/stream/<int:msg_id>")
def stream(msg_id):
    async def generate():
        msg = await tg.get_messages(CHANNEL_ID, msg_id)
        async for chunk in tg.stream_media(msg):
            yield chunk

    return Response(
        asyncio.run(generate()),
        content_type="application/octet-stream"
    )

if __name__ == "__main__":
    tg.start()  # will ask for phone login once
    app.run(host="0.0.0.0", port=8080)
