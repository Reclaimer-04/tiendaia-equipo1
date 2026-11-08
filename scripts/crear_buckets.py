import os
import sys
import boto3

s3 = boto3.client("s3", endpoint_url=os.getenv("S3_ENDPOINT"),
                  aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
                  aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
                  region_name=os.getenv("S3_REGION", "us-east-1"))

existentes = {b["Name"] for b in s3.list_buckets()["Buckets"]}

for nombre in sys.argv[1:]:
    if nombre in existentes:
        print("ya existe:", nombre)
    else:
        s3.create_bucket(Bucket=nombre)
        print("creado:", nombre)