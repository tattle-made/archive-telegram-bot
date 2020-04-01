from tattle_helper import register_post, upload_file

data = {
    "type" : "image",
    "data" : "",
    "filename": "asdf",
    "userId" : 169
}

response = upload_file(file_name='denny.txt')
print(response)

# register_post(data)