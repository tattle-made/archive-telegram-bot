import os
import json
import requests
from logger import log
from dotenv import load_dotenv
load_dotenv()

API_BASE_URL = "https://archive-server-dev.tattle.co.in"
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


# s3 stuff
# import boto3
# initiliaze s3
# s3 = boto3.client("s3",aws_access_key_id=os.environ.get('S3_ACCESS_KEY'),aws_secret_access_key=os.environ.get('S3_SECRET_ACCESS_KEY'))
# s3.upload_fileobj(data,bucket_name,file_name,ExtraArgs={"ACL": acl,"ContentType": file_name.split(".")[-1]})


#mongo stuff
# from pymongo import MongoClient
# client = MongoClient("mongodb+srv://"+os.environ.get("TGM_DB_USERNAME")+":"+os.environ.get("TGM_DB_PASSWORD")+"@tattle-data-fkpmg.mongodb.net/test?retryWrites=true&w=majority&ssl=true&ssl_cert_reqs=CERT_NONE")
# db = client[os.environ.get("TGM_DB_NAME")]
# return db[required_collection].insert_one(document)
# return db[required_collection].update_one(find_query,update_query,upsert)