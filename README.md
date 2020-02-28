# Tattle archive's telegram bot interface


## Dev Notes

Please ensure that your environment has the following required  variables
```
ACCESS_TOKEN=
PORT=
S3_ACCESS_KEY=
S3_SECRET_ACCESS_KEY=
BUCKET_NAME=
DB_PASSWORD=
TGM_DB_USERNAME=
TGM_DB_PASSWORD=
```


# Debug Notes
Incoming messages are logged to stdout. they are prefixed with a timestamp of the format YYYY-MM-DD hh:mm:ss.xxxx. The timezone will be the timezone of the server it is deployed on