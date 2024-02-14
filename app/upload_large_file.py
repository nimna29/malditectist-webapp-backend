from fastapi import File, UploadFile, Form, APIRouter
from fastapi.responses import JSONResponse
import threading
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import os
from .ml import classify_file
import time
import asyncio
import json
from .firebase import upload_to_firebase

router = APIRouter()


# Optionally add an OPTIONS route handler
@router.options("/api/upload_large_file/")
async def options_upload_large_file():
    return {"message": "Allow: GET, POST, OPTIONS"}


# Load environment variables from the .env file
load_dotenv()

# Read the MAX_WORKERS environment variable and convert it to an integer
MAX_WORKERS = int(os.getenv('MAX_WORKERS', 5))

# Use the MAX_WORKERS value when creating the ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

# Add a global counter and a Lock for thread safety
active_threads_counter = 0
counter_lock = threading.Lock()

# Directory to store result files
RESULTS_DIRECTORY = "app/results/"


@router.post("/api/upload_large_file/", tags=["Upload Large File"])
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

