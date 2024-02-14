from fastapi import FastAPI
from .upload_file import router as upload_file_router
from .upload_large_file import router as upload_large_file_router
from .search_result import router as search_result_router
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="MalDitectist",
    description="FastAPI for MalDitectist",
    version="2.1.0"
)

# Add CORS middleware to allow all origins (replace '*' with your frontend URL in production)
# Define the allowed origins for your frontend (replace with your actual frontend URL)
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://nimna29.github.io/malditectist-webapp-frontend/",
    "http://nimna29.github.io/malditectist-webapp-frontend/"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    # allow_methods=["*"],
    allow_headers=["*"],
)

# Root route
@app.get("/", tags=['Root'])
def home():
    return {'message': 'Welcome to MalDitectist'}


app.include_router(upload_file_router)
app.include_router(upload_large_file_router)
app.include_router(search_result_router)


import logging

logging.basicConfig(level=logging.INFO)
