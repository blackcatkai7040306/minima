import os
import logging
import asyncio
import firebase_admin
from fastapi import FastAPI
from requestor import request_data
from contextlib import asynccontextmanager
from firebase_admin import credentials, firestore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COLLECTION_NAME = os.environ.get("FIRESTORE_COLLECTION_NAME")
TASKS_COLLECTION = os.environ.get("TASKS_COLLECTION")
FIREBASE_KEY_FILE = os.environ.get("FIREBASE_KEY_FILE")
USER_ID = os.environ.get("USER_ID")

app = FastAPI()

cred = credentials.Certificate(FIREBASE_KEY_FILE)
firebase_admin.initialize_app(cred)

db = firestore.client()

async def poll_firestore():
    logger.info(f"Polling Firestore collection: {COLLECTION_NAME}")
    while True:
        try:
            docs = db.collection(COLLECTION_NAME).document(USER_ID).collection(TASKS_COLLECTION).stream()
            for doc in docs:
                data = doc.to_dict()
                if data['status'] == 'PENDING':
                    response = await request_data(data['request'])
                    if 'error' not in response:
                        logger.info(f"Updating Firestore document: {doc.id}")
                        doc_ref = db.collection(COLLECTION_NAME).document(USER_ID).collection(TASKS_COLLECTION).document(doc.id)
                        doc_ref.update({
                            'status': 'COMPLETED',
                            'links': response['result']['links'],
                            'result': response['result']['output']
                        })
                    else:
                        logger.error(f"Error in processing request: {response['error']}")
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Error in polling Firestore collection: {e}")
            await asyncio.sleep(0.5)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Firestore polling")
    poll_task = asyncio.create_task(poll_firestore())
    yield
    poll_task.cancel()


def create_app() -> FastAPI:
    app = FastAPI(
        openapi_url="/linker/openapi.json",
        docs_url="/linker/docs",
        lifespan=lifespan
    )
    return app

app = create_app()