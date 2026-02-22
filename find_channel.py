from pyrogram import Client

API_ID = 33433044
API_HASH = "004b07359a56a200099594631dd125d7"


with Client("myaccount", api_id=API_ID, api_hash=API_HASH) as app:
    me = app.get_me()
    print("Logged in as:", me.first_name, me.id)
    print("---- DIALOGS ----")
    for dialog in app.get_dialogs():
        print(dialog.chat.title, dialog.chat.id)
