import os
import json
import boto3
import requests
from logger import log, logError
from dotenv import load_dotenv
load_dotenv()

s3 = boto3.client("s3",aws_access_key_id=os.environ.get('S3_ACCESS_KEY'),aws_secret_access_key=os.environ.get('S3_SECRET_ACCESS_KEY'))

API_BASE_URL = "https://archive-server.tattle.co.in"
# API_BASE_URL = "https://postman-echo.com/post"
ARCHIVE_TOKEN = os.environ.get('ARCHIVE_TOKEN')

def register_post(data):
	"""
		registers a post on archive server
	"""
	url_to_post_to = API_BASE_URL+"/api/posts"
	payload = json.dumps(data)
	headers = {
		'token': ARCHIVE_TOKEN,
		'Content-Type': "application/json",
		'cache-control': "no-cache",
    }

	try:
		r = requests.post(url_to_post_to, data=payload, headers=headers)

		if r.status_code==200:
			log('STATUS CODE 200 \n'+json.dumps(r.json(), indent=2))
		else:
			log('STATUS CODE '+str(r.status_code)+'\n '+r.text)
	except:
		log('error with API call')


def upload_file(file_name, s3=s3 ,acl="public-read"):
	bucket_name = os.environ.get('TGM_BUCKET_NAME')
	#opens file, reads it, and uploads it to the S3 bucket.
	try:
		with open(file_name, 'rb') as data:
			s3.upload_fileobj(data,bucket_name,file_name,ExtraArgs={"ACL": acl,"ContentType": file_name.split(".")[-1]})
	except:
		logError('ERROR_S3_UPLOAD of '+file_name)
	
	file_url = "https://s3.ap-south-1.amazonaws.com/"+bucket_name+"/"+file_name
	return file_url

def upload_file(file_name, s3=s3 ,acl="public-read"):
	bucket_name = os.environ.get('TGM_BUCKET_NAME')
	#opens file, reads it, and uploads it to the S3 bucket.
	try:
		with open(file_name, 'rb') as data:
			s3.upload_fileobj(data,bucket_name,file_name,ExtraArgs={"ACL": acl,"ContentType": file_name.split(".")[-1]})
	except:
		logError('ERROR_S3_UPLOAD of '+file_name)
	
	file_url = "https://s3.ap-south-1.amazonaws.com/"+bucket_name+"/"+file_name
	return file_url