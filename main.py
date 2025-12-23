from contextlib import asynccontextmanager

from beanie import init_beanie
from fastapi import FastAPI

from config import settings
from db import db
from logging_config import get_logger, setup_logging
from modules.auth.router import auth_router, setup_auth

setup_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database...")
    await init_beanie(database=db, document_models=[])
    logger.info("Database initialized")
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
setup_auth(app)
app.include_router(auth_router)
