import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from core.config import Config

app = FastAPI()

# 開発モードのみOpenAPIを有効にする
if Config.DEBUG is True:
    app = FastAPI()
else:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

# CPRS対策
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def get_root():
    return {"Hello": "World"}


# リクエストの中身を取得して表示
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    if Config.DEBUG is True:
        print("header:", dict(request.headers))
        print("body:", await request.body())

    response = await call_next(request)
    return response


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=5000, log_level="info", workers=4)
    uvicorn.run("main:app", host="127.0.0.1", port=5000, log_level="info", workers=4)
