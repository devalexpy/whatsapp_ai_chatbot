from pymongo import AsyncMongoClient

from config import settings

client = AsyncMongoClient(settings.mongo_uri)
db = client.whatsapp_ai_chatbot
