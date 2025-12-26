from contextlib import asynccontextmanager

from beanie import init_beanie
from fastapi import FastAPI

from config import settings
from db import db
from logging_config import get_logger, setup_logging
from modules.auth.router import auth_router, setup_auth
from modules.products.models import (
    Product,
    ProductOption,
    ProductOptionGroup,
    ProductVariant,
)
from modules.products.router import (
    option_groups_router,
    options_router,
    products_router,
    variants_router,
)
from modules.users.models import User
from modules.users.router import users_router

setup_logging(settings.log_level)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database...")
    await init_beanie(
        database=db,
        document_models=[
            User,
            Product,
            ProductVariant,
            ProductOptionGroup,
            ProductOption,
        ],
    )
    logger.info("Database initialized")
    yield


app = FastAPI(
    title=settings.app_name,
    description="""
## 🚀 WhatsApp AI Chatbot API

This API allows you to manage products, variants, and options for your business catalog.

### 📦 Available Modules:

* **Authentication** - Google OAuth login and JWT token management
* **Users** - User profile information
* **Products** - Full CRUD for products with images
* **Variants** - Different versions of a product (sizes, flavors)
* **Option Groups** - Customization groupings (Extra Toppings, Sauces)
* **Options** - Individual options within each group

### 🖼️ Image Upload

Images are uploaded using presigned URLs:
1. Get URL: `POST /{entity}/image/upload-url`
2. Upload file: `PUT` to the URL with appropriate `Content-Type`
3. Confirm: `POST /{entity}/image/confirm`

### 🔐 Authentication

All endpoints (except `/auth/*`) require a JWT token in the header:
```
Authorization: Bearer <token>
```
""",
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "🔐 Auth",
            "description": "Google OAuth authentication and session management",
        },
        {
            "name": "👤 Users",
            "description": "Authenticated user information",
        },
        {
            "name": "🛍️ Products",
            "description": "Main catalog product management",
        },
        {
            "name": "📦 Product Variants",
            "description": "Product variants (sizes, flavors, presentations)",
        },
        {
            "name": "⚙️ Option Groups",
            "description": "Customizable option groupings (Extra Toppings, Sauces)",
        },
        {
            "name": "🎯 Product Options",
            "description": "Individual options within each group",
        },
    ],
    swagger_ui_parameters={
        "defaultModelsExpandDepth": 3,
        "defaultModelExpandDepth": 3,
        "docExpansion": "list",
        "filter": True,
        "showExtensions": True,
        "showCommonExtensions": True,
    },
)
setup_auth(app)

# ────────────────────────────────────────────────────────────
# Auth & Users
# ────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(users_router)

# ────────────────────────────────────────────────────────────
# Products & Related
# ────────────────────────────────────────────────────────────
app.include_router(products_router)
app.include_router(variants_router)
app.include_router(option_groups_router)
app.include_router(options_router)
