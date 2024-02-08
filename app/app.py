from fastapi import FastAPI


app = FastAPI(
    title="MalDitectist",
    description="FastAPI for MalDitectist",
    version="2.0.0"
)

# Root route
@app.get("/", tags=['Root'])
def home():
    return {'message': 'Welcome to MalDitectist'}

