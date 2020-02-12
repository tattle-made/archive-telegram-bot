import os
import sys
import json 
import boto3
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
@run_async
def start(update, context):
	#start message
	context.bot.send_message(chat_id=update.effective_chat.id, text="Hey! \n\nI'm the Tattle Bot. Here are some instructions to use me:\n\n1. You can send whatever content to me that you'd like. All mediums : Text, Video, and Photos are allowed.\n2. You can tag your content using hashtags. When uploading photos or videos you can mention the tags in the caption, with text you can just tag it at the end or in the beginning(anywhere else in the text will also work).\n3. You can edit your messages after you've sent them, we'll update them in our database accordingly.\n 4. In case you miss tagging a message, you can reply to that message and insert the tags required. Only tags will be extracted, so please don't write text while replying to messages.")

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
	update_document({'message_id': message_json.reply_to_message.message_id},{"$set": {"tags": new_tags}},'messages')

def new_tags(message_json,current_document,all_tags):
	#adds or replaces tags in messages that had no tags or in case of edits
	new_tags = all_tags
	update_document({'message_id': message_json.reply_to_message.message_id},{"$set": {"tags": new_tags}},'messages')

def error_message(message_json):
	#standard error message
	context.bot.send_message(chat_id=message_json.chat.id,text="Something went wrong with registering these tags, apologies for the same.")

def reply_to_messages(message_json,edit_flag):

	all_tags = entity_extraction(message_json.entities,message_json.text)

	if(all_tags is not None):
		#first finds the document that the reply is being done to
		current_document = find_document({'message_id': message_json.reply_to_message.message_id},'messages')
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

def edit_message(message_json,final_dict,content_type,context):
	tags = []
	#check content type before processing the data
	if(content_type=='text'):
		final_dict = process_text(message_json,final_dict,message_json['text'],False)
	else:
		final_dict = process_media(message_json,final_dict,content_type,context,False)
	
	#in case message is being edited, we first find the document being edited
	current_document = find_document({'message_id':message_json.message_id},'messages')
	
	#we check if the document had any existing tags, if so we store them before deleting the document
	#FLAW IN CODE : If existing tags are being edited, it doesn't reflect this way. NEED TO FIX.
	try:
		tags = current_document['tags']
	except KeyError:
		tags = None
	#add tags to final dict for new, edited document
	if(tags is not None):
		final_dict['tags'] = tags
	
	#delete the document
	delete_document({'message_id':message_json.message_id},'messages')
	#insert edited document
	insert_document(final_dict,'messages')

def process_text(message_json, final_dict,message_content,caption_flag):
	#check if we're processing a caption or a text message
	if(caption_flag):
		all_tags = entity_extraction(message_json['caption_entities'],message_content)
	else:
		all_tags = entity_extraction(message_json['entities'],message_content)
	#check if any tags are present
	if(all_tags is not None):
		final_dict['tags'] = all_tags

	if(bool(message_content)):
		#cleans out the hashtags
		modified_message = re.sub(r'#\w+','',message_content)
		#removes all excessive spacing
		cleaned_message = re.sub(' +', ' ',modified_message)
		#changes key based on whether it is a caption or not
		if(caption_flag):
			final_dict['caption'] = cleaned_message.strip() #removing leading and trailing spaces
		else:
			final_dict['text'] = cleaned_message.strip()
	print(final_dict)
	return final_dict

def upload_file(s3,file_name,acl="public-read"):
	bucket_name = os.environ.get('BUCKET_NAME')
	#opens file, reads it, and uploads it to the S3 bucket.
	with open(file_name, 'rb') as data:
		s3.upload_fileobj(data,bucket_name,file_name,ExtraArgs={"ACL": acl,"ContentType": file_name.split(".")[-1]})
	
	#just for testing
	# BASE_URL = "http://archive-telegram-bot.tattle.co.in.s3.amazonaws.com/645.jpeg"
	# print("{}{}".format(BASE_URL, file_name))

def process_media(message_json,final_dict,content_type,context,creation_flag):
	
	#check if content type is photo, and constructs dict and file_name appropriately
	if(content_type=='photo'):
		final_dict['photo'] = [{'file_id':each_photo.file_id,'width':each_photo.width,'height':each_photo.height,'file_size':each_photo.file_size} for each_photo in message_json.photo]
		file_id = message_json.photo[-1].file_id
		file_name = str(message_json.message_id)+'.jpeg'

	#same with video as above
	elif(content_type=='video'):
		final_dict['video']	= {'file_id':message_json.video.file_id,'width':message_json.video.width,'height':message_json.video.height,'duration':message_json.video.duration,'thumb':{'file_id':message_json.video.thumb.file_id,'width':message_json.video.thumb.width,'height':message_json.video.thumb.height,'file_size':message_json.video.thumb.file_size},'mime_type':message_json.video.mime_type,'file_size':message_json.video.file_size}
		file_id = message_json.video.file_id
		file_type = str(message_json.video.mime_type).split("/")[-1]
		file_name = str(message_json.message_id)+"."+file_type
	#process_media is only called from two places, one of which is when message is edited. Since we don't want duplicates, we set a flag to differentiate.
	if(creation_flag):
		try:
			new_file = context.bot.get_file(file_id)
			new_file.download(file_name) #downloads the file
			final_dict['file_name'] = file_name 
			s3 = boto3.client("s3",aws_access_key_id=os.environ.get('S3_ACCESS_KEY'),aws_secret_access_key=os.environ.get('S3_SECRET_ACCESS_KEY'))
			upload_file(s3,file_name) #uploads to S3
			os.remove(file_name) #removes it from local runtime
		except:
			logging.debug("The file_name when the error happened is: {}".format(file_name))
			raise
	#process any caption or text found
	final_dict = process_text(message_json, final_dict, message_json.caption,True)
	return final_dict

@run_async
def storing_data(update, context):
	final_dict = {}
	# print(update)
	#selects just the effective_message part
	relevant_section = update.effective_message
	#some general data appended to each dict
	final_dict['message_id'] = relevant_section['message_id']
	final_dict['date'] = relevant_section['date']
	final_dict['from'] = {'id':relevant_section.from_user.id,'type':relevant_section.chat.type,'first_name':relevant_section.from_user.first_name,'last_name':relevant_section.from_user.last_name,'username':relevant_section.from_user.username,'is_bot':relevant_section.from_user.is_bot}
	content_type = determine_type(relevant_section)
	final_dict['content_type'] = content_type
	#checks if the request is that of an edition
	if(relevant_section.edit_date):
		#if yes, checks if the edited message was replying to another message
		if(relevant_section.reply_to_message):
			#if yes, then deals with it by setting edit flag to True
			reply_to_messages(relevant_section,True)
			return
		else:
			#else, just edits the message normally
			edit_message(relevant_section,final_dict,content_type,context)
			return
	#if the message is a reply, then respond appropriately
	if(relevant_section.reply_to_message):
		#edit flag is set to false because we're just handling simple reply
		reply_to_messages(relevant_section,False)
		return

	if(content_type == 'text'):
		#if new text message, process it and then insert it in the database
		final_dict = process_text(relevant_section,final_dict,relevant_section['text'],False)
		insert_document(final_dict,'messages')
	else:
		final_dict = process_media(relevant_section,final_dict,content_type,context,True)
		insert_document(final_dict,'messages')

	context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)

def stop_and_restart():
	"""Gracefully stop the Updater and replace the current process with a new one"""
	updater.stop()
	os.execl(sys.executable, sys.executable, *sys.argv)

def restart(update, context):
	update.message.reply_text('Bot is restarting...')
	Thread(target=stop_and_restart).start()

#initialises database connection
client = MongoClient()
# client = MongoClient("mongodb+srv://thenerdyouknow:"+os.environ.get("DB_PASSWORD")+"@cluster0-dxaod.mongodb.net/test?retryWrites=true&w=majority")
db = client.telegram_bot

updater = Updater(token=TOKEN, use_context=True, workers=32)
dispatcher = updater.dispatcher
start_handler = CommandHandler('start', start)
storing_data_handler = MessageHandler(Filters.all,storing_data)
restart_handler = CommandHandler('r', restart, filters=Filters.user(username='@thenerdyouknow'))

dispatcher.add_handler(restart_handler)
dispatcher.add_handler(start_handler)
dispatcher.add_handler(storing_data_handler)

updater.start_webhook(listen="0.0.0.0",
	port=PORT,
	url_path=TOKEN)

updater.bot.set_webhook("https://services-dev.tattle.co.in/telegram-bot" + TOKEN)
# updater.start_polling()
# updater.idle()

print('server starting')