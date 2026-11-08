import os
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, ContentSettings, generate_blob_sas, BlobSasPermissions

class AlmacenAzure:
    def __init__(self):
        # Conexión local a Azurite (cuenta de desarrollo predeterminada)
        connection_string = "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://azurite:10000/devstoreaccount1;"
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.bucket = os.getenv("S3_BUCKET", "tiendaia-imagenes")
        self.container_client = self.blob_service_client.get_container_client(self.bucket)
        
        if not self.container_client.exists():
            self.container_client.create_container()

    def subir(self, clave: str, datos: bytes, tipo: str, metadatos: dict) -> None:
        blob_client = self.container_client.get_blob_client(clave)
        settings = ContentSettings(content_type=tipo)
        blob_client.upload_blob(datos, overwrite=True, content_settings=settings, metadata=metadatos)

    def url(self, clave: str, segundos: int = 3600) -> str:
        sas_token = generate_blob_sas(
            account_name="devstoreaccount1",
            container_name=self.bucket,
            blob_name=clave,
            account_key="Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==",
            permission=BlobSasPermissions(read=True),
            expiry=datetime.utcnow() + timedelta(seconds=segundos)
        )
        url_publica = os.getenv("S3_PUBLIC_ENDPOINT_AZURE", "http://localhost:10000/devstoreaccount1")
        return f"{url_publica}/{self.bucket}/{clave}?{sas_token}"

    def eliminar(self, clave: str) -> None:
        blob_client = self.container_client.get_blob_client(clave)
        if blob_client.exists():
            blob_client.delete_blob()