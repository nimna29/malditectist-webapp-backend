from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends
from fastapi.responses import JSONResponse
from datetime import timedelta
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from .firebase import bucket
from dotenv import load_dotenv
import os
from threading import Lock
from .ml import classify_file
import time
import asyncio
import json


# Load environment variables from the .env file
load_dotenv()

app = FastAPI(
    title="MalDitectist",
    description="FastAPI for MalDitectist",
    version="2.0.0"
)


# Read the MAX_WORKERS environment variable and convert it to an integer
MAX_WORKERS = int(os.getenv('MAX_WORKERS', 5))

# Use the MAX_WORKERS value when creating the ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

# Add a global counter and a Lock for thread safety
active_threads_counter = 0
counter_lock = threading.Lock()

# Directory to store result files
RESULTS_DIRECTORY = "app/results/"


# Root route
@app.get("/", tags=['Root'])
def home():
    return {'message': 'Welcome to MalDitectist'}


@app.post("/api/upload_file/")
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


async def save_result_to_file(result_id, result):
    # Create a directory if it doesn't exist
    os.makedirs(RESULTS_DIRECTORY, exist_ok=True)

    # Save the result to a file in a separate thread
    await asyncio.to_thread(write_result_to_file, result_id, result)

def write_result_to_file(result_id, result):
    file_path = os.path.join(RESULTS_DIRECTORY, f"{result_id}.txt")
    with open(file_path, 'w') as file:
        # Convert the dictionary to a JSON string
        json_result = json.dumps(result)
        file.write(json_result)
    threading.Thread(target=delete_file_after_delay, args=(file_path, 30 * 60)).start()

def delete_file_after_delay(file_path, delay):
    # Sleep for the specified delay and then delete the file
    time.sleep(delay)
    os.remove(file_path)

async def process_large_file(file_url, result_id, blob):
    global active_threads_counter
    global counter_lock

    # Pass the file to the classify_file function for analysis
    result = await classify_file(file_url)

    # Save the result to a file
    await save_result_to_file(result_id, result)  # Await the save_result_to_file coroutine

    # Delete the uploaded file from Firebase Storage
    blob.delete()

    # Decrease the active threads counter
    with counter_lock:
        active_threads_counter -= 1


@app.post("/api/upload_large_file/")
async def upload_large_file(
    file: UploadFile = File(...),
    unique_key: str = Form(...),
    result_id: str = Form(...),
):
    global active_threads_counter
    global counter_lock

    # Upload the file to Firebase Storage, and get the filename, blob, and signed URL
    filename, blob, file_url = upload_to_firebase(file.file, unique_key)

    # Check if the number of active threads exceeds the MAX_WORKERS limit
    with counter_lock:
        if active_threads_counter >= MAX_WORKERS:
            return JSONResponse(
                content={'error': 'Server is busy. Please try again later.'},
                status_code=503,
            )
        active_threads_counter += 1

    # Start processing the large file with asyncio.create_task
    asyncio.create_task(process_large_file(file_url, result_id, blob))

    # Return the result_id to the frontend
    return JSONResponse(content={'result_id': result_id}, status_code=200)

@app.get("/api/search_result/{result_id}/")
async def search_result(result_id: str):
    # Read the result from the file
    file_path = os.path.join(RESULTS_DIRECTORY, f"{result_id}.txt")
    try:
        with open(file_path, 'r') as file:
            # Read the JSON string from the file and parse it
            result = json.loads(file.read())
        return JSONResponse(content=result, status_code=200)
    except FileNotFoundError:
        return JSONResponse(
            content={'error': 'Result not found or expired.'},
            status_code=404,
        )


def get_file_and_unique_key(request):
    """
    Retrieves the file and unique_key from the request, and returns any errors.
    """
    file = request.FILES.get('file')
    if file is None:
        return None, None, JSONResponse(
            content={'error': 'File not found in request'}, 
            status_code=400)

    if not file.name.endswith('.exe'):
        return None, None, JSONResponse(
            content={'error': 'Invalid file type. Only .exe files are supported.'},
            status_code=400)

    unique_key = request.data.get('unique_key')
    if unique_key is None:
        return None, None, JSONResponse(
            content={'error': 'Unique key not found in request.'}, 
            status_code=400)

    return file, unique_key, None


def upload_to_firebase(file, unique_key):
    """
    Uploads the given file to Firebase Storage, and returns the filename, blob, and signed URL.
    """
    filename = f"{unique_key}_{file.name}"
    blob = bucket.blob(filename)
    blob.upload_from_file(file)

    file_url = blob.generate_signed_url(
        expiration=timedelta(minutes=30), method='GET')

    return filename, blob, file_url

