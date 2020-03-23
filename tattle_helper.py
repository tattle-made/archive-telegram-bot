import os
import json
import requests
from logger import log
from dotenv import load_dotenv
load_dotenv()

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