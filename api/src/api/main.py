from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from opperai import Opper

from .clients.couchbase import CouchbaseChatClient
from .routes import router
from .utils import log
from . import conf

log.init(conf.get_log_level())
logger = log.get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    cb_conf = conf.get_couchbase_conf()
    app.state.db = CouchbaseChatClient(
        url=cb_conf.url,
        username=cb_conf.username,
        password=cb_conf.password,
        bucket_name=cb_conf.bucket,
        scope=cb_conf.scope
    )
    try:
        app.state.db.connect()
        app.state.db.init()  # Ensure collections are initialized
        logger.info("Connected to Couchbase database and initialized collections")
    except Exception as e:
        logger.warning(f"Couldn't connect to Couchbase - retrying on next request. Error: {e}")
    app.state.opper = Opper(api_key=conf.get_opper_api_key())

    yield

app = FastAPI(
    title="Customer Support Chat API",
    version="1.0.0",
    docs_url="/docs",
    lifespan=lifespan
)
app.include_router(router, prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def main():
    if not conf.validate():
        raise ValueError("Invalid configuration.")

    http_conf = conf.get_http_conf()
    logger.info(f"Starting API on port {http_conf.port}")
    uvicorn.run(
        "api.main:app",
        host=http_conf.host,
        port=http_conf.port,
        reload=http_conf.autoreload,
        log_level="debug" if http_conf.debug else "info",
        log_config=None
    )
