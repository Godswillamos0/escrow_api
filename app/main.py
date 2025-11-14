from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db import models, database
from api.v1 import router
from redis import Redis



# Create tables
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    app.state.redis = Redis(host='localhost',port=6379)


@app.on_event("shutdown")
async def shutdown_event():
    app.state.redis.close()


app.include_router(
    router=router.router,
    )



# Run app
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)