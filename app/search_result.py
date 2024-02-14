from fastapi import APIRouter
from fastapi.responses import JSONResponse
import os
import json

router = APIRouter()


# Optionally add an OPTIONS route handler
@router.options("/api/search_result/")
async def options_search_result():
    return {"message": "Allow: GET, OPTIONS"}


# Directory to store result files
RESULTS_DIRECTORY = "app/results/"


@router.get("/api/search_result/{result_id}/", tags=["Search Result"])
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

