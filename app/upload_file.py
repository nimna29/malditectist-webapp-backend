from fastapi import File, UploadFile, Form, APIRouter
from fastapi.responses import JSONResponse
from .firebase import upload_to_firebase
from .ml import classify_file

router = APIRouter()


@router.post("/api/upload_file/", tags=["Upload File"])
async def upload_file(file: UploadFile = File(...), unique_key: str = Form(...)):
    """
    Handles the file upload and classification for small files.
    """
    # Upload the file to Firebase Storage, and get the filename, blob, and signed URL
    filename, blob, file_url = upload_to_firebase(file.file, unique_key)

    # Pass the file to the classify_file function for analysis
    result = await classify_file(file_url)
    if result is None:
        return JSONResponse(content={'error': 'Failed to classify file'}, status_code=500)

    # Delete the uploaded file from Firebase Storage
    blob.delete()

    # Return the result of the classification to the frontend
    return result