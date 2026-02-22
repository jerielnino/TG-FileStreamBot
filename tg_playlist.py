import asyncio
from pyrogram import Client
from flask import Flask, Response

API_ID = 33433044
API_HASH = "004b07359a56a200099594631dd125d7"
#BOT_TOKEN = "7905710256:AAGBSDX83F4ftuOKgSBxj981k0ET8N0eG5M"
# 🔥 USE LINK INSTEAD OF NUMERIC ID
CHANNEL_REF = "https://t.me/c/3726584253"
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8080
SERVER_IP = "192.168.20.50"  # your phone IP

app = Flask(__name__)

tg = Client("myaccount", api_id=API_ID, api_hash=API_HASH)
tg.start()

print("Telegram client started")


@app.route("/playlist.m3u")
def playlist():
    m3u = "#EXTM3U\n"

    for msg in tg.get_chat_history(CHANNEL_REF, limit=200):
        if msg.video or msg.document:

            if msg.video:
                name = msg.video.file_name
            else:
                name = msg.document.file_name

            if not name:
                name = f"File {msg.id}"

            m3u += f"#EXTINF:-1,{name}\n"
            m3u += f"http://{SERVER_IP}:{SERVER_PORT}/stream/{msg.id}\n"

    return m3u


@app.route("/stream/<int:msg_id>")
def stream(msg_id):

    msg = tg.get_messages(CHANNEL_REF, msg_id)

    def generate():
        for chunk in tg.stream_media(msg):
            yield chunk

    return Response(generate(), content_type="application/octet-stream")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=SERVER_PORT)
