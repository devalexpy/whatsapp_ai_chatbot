from fastapi import FastAPI

from modules.auth.router import auth_router, setup_auth

app = FastAPI(title="WhatsApp AI Chatbot")
setup_auth(app)
app.include_router(auth_router)
