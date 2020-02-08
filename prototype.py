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

# Calls for Database modification and reads start
def insert_document(document,required_collection):
	return db[required_collection].insert_one(document)

def find_document(query,required_collection):
	return db[required_collection].find_one(query)

def update_document(find_query,update_query,required_collection,upsert=False):
	return db[required_collection].update_one(find_query,update_query,upsert)

def delete_document(find_query,required_collection):
	return db[required_collection].delete_one(find_query)
# Calls for Database modification and reads end

def start(update, context):
	#start message
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

def entity_extraction(all_entities, message_content):
	#entity extraction, which basically extracts all the hashtags out of the message
	list_of_tags = []
	if(bool(all_entities)):
		#checks if there are any entities, and if so loops over them
		for each_entity in all_entities:
			if(each_entity['type'] == 'hashtag'):
				# string slicing based on offset and length values
				tag = message_content[each_entity['offset']:(each_entity['offset']+each_entity['length'])]
				list_of_tags.append(tag)
	if(bool(list_of_tags)):
		#converts to set to remove duplicates
		return list(set(list_of_tags))
	else:
		return None 

def combine_tags(message_json,current_document,all_tags):
	#combines the old tags and new tags in case replies to messages that had tags in them
	new_tags = list(set(current_document['tags'] + all_tags))
	update_document({'message_id': message_json.reply_to_message.message_id},{"$set": {"tags": new_tags}},'text_messages')

def new_tags(message_json,current_document,all_tags):
	#adds or replaces tags in messages that had no tags or in case of edits
	new_tags = all_tags
	update_document({'message_id': message_json.reply_to_message.message_id},{"$set": {"tags": new_tags}},'text_messages')

def error_message(message_json):
	#standard error message
	context.bot.send_message(chat_id=message_json.chat.id,text="Something went wrong with registering these tags, apologies for the same.")

def reply_to_messages(message_json,edit_flag):
	all_tags = entity_extraction(message_json.entities,message_json.text)
	if(all_tags is not None):
		#first finds the document that the reply is being done to
		current_document = find_document({'message_id': message_json.reply_to_message.message_id},'text_messages')
		
		#if the edit flag is true, it means that the message that is replying to other message is being edited
		if(edit_flag):
			try:
				#in which case, we just replace the previous tags with the new, edited tags as the replies have to be just entities
				new_tags(message_json,current_document,all_tags)
				return
			except:
				#otherwise, through an error message and log the exception
				error_message()
				raise

		try:
			#in case of regular replies, just combine tags if message that is being replied to also has tags
			combine_tags(message_json,current_document,all_tags)
		except KeyError:
			#if not, then add the tags from the replies
			new_tags(message_json,current_document,all_tags)
		except:
			#or, throw an error message and log
			error_message()
			raise

def edit_message(message_json,final_dict):
	tags = []
	#in case message is being edited, we first find the document being edited
	current_document = find_document({'message_id':message_json.message_id},'text_messages')
	
	#we check if the document had any existing tags, if so we store them before deleting the document
	try:
		tags = current_document['tags']
	except KeyError:
		tags = None
	#delete the document
	delete_document({'message_id':message_json.message_id},'text_messages')
	
	#add tags to final dict for new, edited document
	if(tags is not None):
		final_dict['tags'] = tags
	#insert edited document
	insert_document(process_text(message_json,final_dict),'text_messages')

def process_text(message_json, final_dict):
	message_content = message_json['text']
	all_tags = entity_extraction(message_json['entities'],message_content)
	if(all_tags is not None):
		final_dict['tags'] = all_tags
	#cleans out the hashtags
	modified_message = re.sub(r'#\w+','',message_content)
	#removes all excessive spacing
	cleaned_message = re.sub(' +', ' ',modified_message)
	final_dict['text'] = cleaned_message.strip() #removing leading and trailing spaces
	return final_dict

def storing_data(update, context):
	final_dict = {}
	#selects just the effective_message part
	relevant_section = update.effective_message
	#some general data appended to each dict
	final_dict['message_id'] = relevant_section['message_id']
	final_dict['date'] = relevant_section['date']
	final_dict['from'] = {'id':relevant_section.from_user.id,'type':relevant_section.chat.type,'first_name':relevant_section.from_user.first_name,'last_name':relevant_section.from_user.last_name,'is_bot':relevant_section.from_user.is_bot}
	content_type = determine_type(relevant_section)
	#checks if the request is that of an edition
	if(relevant_section.edit_date):
		#if yes, checks if the edited message was replying to another message
		if(relevant_section.reply_to_message):
			#if yes, then deals with it by setting edit flag to True
			reply_to_messages(relevant_section,True)
			return
		else:
			#else, just edits the message normally
			edit_message(relevant_section,final_dict)
			return
	#if the message is a reply, then respond appropriately
	if(relevant_section.reply_to_message):
		#edit flag is set to false because we're just handling simple reply
		reply_to_messages(relevant_section,False)
		return

	if(content_type == 'text'):
		#if new text message, process it and then insert it in the database
		final_dict = process_text(relevant_section,final_dict)
		insert_document(final_dict,'text_messages')

	context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)

def stop_and_restart():
	"""Gracefully stop the Updater and replace the current process with a new one"""
	updater.stop()
	os.execl(sys.executable, sys.executable, *sys.argv)

def restart(update, context):
	update.message.reply_text('Bot is restarting...')
	Thread(target=stop_and_restart).start()

#initialises database connection
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

