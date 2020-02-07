import os
import sys
import json 
import requests
import telegram
import logging
from threading import Thread
from telegram.ext import CommandHandler, MessageHandler, Updater, Filters, InlineQueryHandler
from telegram import InlineQueryResultArticle, InputTextMessageContent
from telegram.ext.dispatcher import run_async


TOKEN = os.environ.get('ACCESS_TOKEN')
PORT = int(os.environ.get('PORT', '8443'))

logging.basicConfig(filename='telegram_bot_log',filemode='a',format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Hey! \n\nI'm the Tattle Bot. Here are some instructions to use me:\n\n1. You can send whatever content to me that you'd like. All mediums : Text, Video, and Photos(both as a photo and as a file) are allowed.\n2. You can tag your content using hashtags. When uploading photos or videos you can mention the tags in the caption, with text you can just tag it at the end or in the beginning(anywhere else in the text will also work).\n3. You can edit your messages after you've sent them, we'll update them in our database accordingly.\n 4. In case you miss tagging a message, you can reply to that message and insert the tags required. Only tags will be extracted, so please don't write text while replying to messages.")

@run_async
def echo(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)

def caps(update, context):
    text_caps = ' '.join(context.args).upper()
    context.bot.send_message(chat_id=update.effective_chat.id, text=text_caps)

def stop_and_restart():
    """Gracefully stop the Updater and replace the current process with a new one"""
    updater.stop()
    os.execl(sys.executable, sys.executable, *sys.argv)

def restart(update, context):
    update.message.reply_text('Bot is restarting...')
    Thread(target=stop_and_restart).start()


updater = Updater(token=TOKEN, use_context=True, workers=32)
dispatcher = updater.dispatcher
start_handler = CommandHandler('start', start)
echo_handler = MessageHandler(Filters.all,echo)
caps_handler = CommandHandler('caps', caps)
restart_handler = CommandHandler('r', restart, filters=Filters.user(username='@thenerdyouknow'))

dispatcher.add_handler(restart_handler)
dispatcher.add_handler(start_handler)
dispatcher.add_handler(caps_handler)
dispatcher.add_handler(echo_handler)
# dispatcher.add_handler(inline_caps_handler)

updater.start_webhook(listen="0.0.0.0",
                      port=PORT,
                      url_path=TOKEN)

updater.bot.set_webhook("https://tattle-telegram-bot.herokuapp.com/" + TOKEN)
updater.idle()

