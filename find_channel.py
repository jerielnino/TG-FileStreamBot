from pyrogram import Client

API_ID = 33433044
API_HASH = "004b07359a56a200099594631dd125d7"

with Client("myaccount", api_id=API_ID, api_hash=API_HASH) as app:
    for dialog in app.get_dialogs():
        if dialog.chat.type in ["channel", "supergroup"]:
            print("TITLE:", dialog.chat.title)
            print("ID:", dialog.chat.id)
            print("-" * 40)
