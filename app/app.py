from fastapi import FastAPI
from .upload_file import router as upload_file_router
from .upload_large_file import router as upload_large_file_router
from .search_result import router as search_result_router


app = FastAPI(
    title="MalDitectist",
    description="FastAPI for MalDitectist",
    version="2.1.0"
)


# Root route
@app.get("/", tags=['Root'])
def home():
    return {'message': 'Welcome to MalDitectist'}


app.include_router(upload_file_router)
app.include_router(upload_large_file_router)
app.include_router(search_result_router)

