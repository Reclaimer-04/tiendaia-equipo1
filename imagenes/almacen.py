import os
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

class AlmacenS3:
    def __init__(self):
        cred = dict(aws_access_key_id=os.getenv("S3_ACCESS_KEY"),
                    aws_secret_access_key=os.getenv("S3_SECRET_KEY"),
                    region_name=os.getenv("S3_REGION", "us-east-1"),
                    config=Config(signature_version="s3v4"))
        self.bucket = os.environ["S3_BUCKET"]
        self.s3 = boto3.client("s3", endpoint_url=os.getenv("S3_ENDPOINT"), **cred)
        self.firmas = boto3.client("s3", endpoint_url=os.getenv("S3_PUBLIC_ENDPOINT", os.getenv("S3_ENDPOINT")), **cred)
        try:
            self.s3.head_bucket(Bucket=self.bucket)
        except ClientError:
            self.s3.create_bucket(Bucket=self.bucket)

    def subir(self, clave: str, datos: bytes, tipo: str, metadatos: dict) -> None:
        self.s3.put_object(Bucket=self.bucket, Key=clave, Body=datos, ContentType=tipo, Metadata=metadatos)

    def url(self, clave: str, segundos: int = 3600) -> str:
        return self.firmas.generate_presigned_url("get_object", Params={"Bucket": self.bucket, "Key": clave}, ExpiresIn=segundos)

    def eliminar(self, clave: str) -> None:
        self.s3.delete_object(Bucket=self.bucket, Key=clave)