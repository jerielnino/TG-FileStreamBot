import asyncio
from pyrogram import Client
from flask import Flask, Response

API_ID = 33433044
API_HASH = "004b07359a56a200099594631dd125d7"
#BOT_TOKEN = "7905710256:AAGBSDX83F4ftuOKgSBxj981k0ET8N0eG5M"
CHANNEL_ID = -1003726584253
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8080
SERVER_IP = "192.168.20.50"  # your phone IP

app = Flask(__name__)

tg = Client("myaccount", api_id=API_ID, api_hash=API_HASH)

# Start telegram client (NO asyncio here)
tg.start()
print("Telegram client started successfully")

@app.route("/playlist.m3u")
def playlist():

    async def build():
        m3u = "#EXTM3U\n"

        # 🔥 find chat object from dialogs (guaranteed valid)
        target_chat = None
        async for dialog in tg.get_dialogs():
            if dialog.chat.id == CHANNEL_ID:
                target_chat = dialog.chat
                break

        if not target_chat:
            return "Channel not found in dialogs"

        async for msg in tg.get_chat_history(target_chat.id, limit=200):
            if msg.video or msg.document:

                filename = None
                if msg.video:
                    filename = msg.video.file_name
                elif msg.document:
                    filename = msg.document.file_name

                if not filename:
                    filename = f"File {msg.id}"

                m3u += f"#EXTINF:-1,{filename}\n"
                m3u += f"http://{SERVER_IP}:{SERVER_PORT}/stream/{msg.id}\n"

        return m3u

    return asyncio.run(build())


@app.route("/stream/<int:msg_id>")
def stream(msg_id):

    async def generate():

        target_chat = None
        async for dialog in tg.get_dialogs():
            if dialog.chat.id == CHANNEL_ID:
                target_chat = dialog.chat
                break

        if not target_chat:
            return

        msg = await tg.get_messages(target_chat.id, msg_id)

        async for chunk in tg.stream_media(msg):
            yield chunk

    return Response(
        asyncio.run(generate()),
        content_type="application/octet-stream"
    )
    
if __name__ == "__main__":
    app.run(host=SERVER_HOST, port=SERVER_PORT)
