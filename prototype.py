import os
import sys
import json 
import requests
import telegram
import logging
import re
from threading import Thread
from telegram.ext import CommandHandler, MessageHandler, Updater, Filters, InlineQueryHandler
from telegram import InlineQueryResultArticle, InputTextMessageContent
from telegram.ext.dispatcher import run_async
from dotenv import load_dotenv
from pymongo import MongoClient

#loads all environment variables
load_dotenv()

TOKEN = os.environ.get('ACCESS_TOKEN')
PORT = int(os.environ.get('PORT', '8443'))

logging.basicConfig(filename='telegram_bot_log',filemode='a',format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def start(update, context):
	context.bot.send_message(chat_id=update.effective_chat.id, text="Hey! \n\nI'm the Tattle Bot. Here are some instructions to use me:\n\n1. You can send whatever content to me that you'd like. All mediums : Text, Video, and Photos(both as a photo and as a file) are allowed.\n2. You can tag your content using hashtags. When uploading photos or videos you can mention the tags in the caption, with text you can just tag it at the end or in the beginning(anywhere else in the text will also work).\n3. You can edit your messages after you've sent them, we'll update them in our database accordingly.\n 4. In case you miss tagging a message, you can reply to that message and insert the tags required. Only tags will be extracted, so please don't write text while replying to messages.")

def determine_type(message_json):
	#checks what type of content is being passed, and returns the type
	type_of_content = ''
	if(message_json.text):
		type_of_content = 'text'
	elif(message_json.photo):
		type_of_content = 'photo'
	elif(message_json.video):
		type_of_content = 'video'
	return type_of_content

def process_text(message_json, final_dict):
	message_content = message_json['text']
	if(bool(message_json['entities'])):
		list_of_tags = []
		#loops over all entities and extracts hashtags
		for each_entity in message_json['entities']:
			if(each_entity['type'] == 'hashtag'):
				tag = message_content[each_entity['offset']:(each_entity['offset']+each_entity['length'])]
				if tag not in list_of_tags:
					#check so that duplicate tags are not added
					list_of_tags.append(tag)
		if(bool(list_of_tags)):
			#if the list is not empty, then we have some tags available.
			final_dict['tags'] = list_of_tags
	#cleans out the hashtags
	modified_message = re.sub(r'#\w+','',message_content)
	#removes all excessive spacing
	cleaned_message = re.sub(' +', ' ',modified_message)
	final_dict['text'] = cleaned_message
	return final_dict

def storing_data(update, context):
	final_dict = {}
	print(update)
	#selects just the effective_message part
	relevant_section = update.effective_message
	#some general data appended to each dict
	final_dict['message_id'] = relevant_section['message_id']
	final_dict['date'] = relevant_section['date']
	final_dict['from'] = {'id':relevant_section.from_user.id,'type':relevant_section.chat.type,'first_name':relevant_section.from_user.first_name,'last_name':relevant_section.from_user.last_name,'is_bot':relevant_section.from_user.is_bot}
	content_type = determine_type(relevant_section)
	print(content_type)
	if(content_type == 'text'):
		final_dict = process_text(relevant_section,final_dict)
	print(final_dict)

	context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)

def stop_and_restart():
	"""Gracefully stop the Updater and replace the current process with a new one"""
	updater.stop()
	os.execl(sys.executable, sys.executable, *sys.argv)

def restart(update, context):
	update.message.reply_text('Bot is restarting...')
	Thread(target=stop_and_restart).start()

client = MongoClient('mongodb://localhost:27017/')
db = client.telegram_bot

updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher
start_handler = CommandHandler('start', start)
storing_data_handler = MessageHandler(Filters.all,storing_data)
restart_handler = CommandHandler('r', restart, filters=Filters.user(username='@thenerdyouknow'))

dispatcher.add_handler(restart_handler)
dispatcher.add_handler(start_handler)
dispatcher.add_handler(storing_data_handler)
# dispatcher.add_handler(inline_caps_handler)

# updater.start_webhook(listen="0.0.0.0",
#                       port=PORT,
#                       url_path=TOKEN)

# updater.bot.set_webhook("https://tattle-telegram-bot.herokuapp.com/" + TOKEN)
updater.start_polling()
updater.idle()

