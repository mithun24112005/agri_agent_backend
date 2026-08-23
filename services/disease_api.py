import httpx
from fastapi import UploadFile
import io
from config.settings import settings
from schemas.disease import DiseaseAPIResponse

async def predict_disease_from_image(file: UploadFile) -> DiseaseAPIResponse:
    """
    Sends an image file to the external Disease ML server for classification.
    """
    url = f"{settings.disease_api_url.rstrip('/')}/disease/predict"
    
    # Read the file content
    content = await file.read()
    
    # Send as multipart/form-data
    files = {'file': (file.filename, content, file.content_type)}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, files=files)
        response.raise_for_status()
        
        data = response.json()
        return DiseaseAPIResponse(**data)

async def predict_disease_from_path(file_path: str) -> DiseaseAPIResponse:
    """
    Sends an image file from path to the external Disease ML server for classification.
    """
    url = f"{settings.disease_api_url.rstrip('/')}/disease/predict"
    import os
    import asyncio
    
    filename = os.path.basename(file_path)
    
    def read_file():
        with open(file_path, 'rb') as f:
            return f.read()
            
    content = await asyncio.to_thread(read_file)
        
    # Assume image/jpeg for simplicity based on extension could be improved
    files = {'file': (filename, content, "image/jpeg")}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, files=files)
        response.raise_for_status()
        
        data = response.json()
        return DiseaseAPIResponse(**data)

