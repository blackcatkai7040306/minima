import os
import uuid
import torch
import logging
from qdrant_client import QdrantClient
from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client.http.models import Distance, VectorParams
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    TextLoader,
    CSVLoader,
    Docx2txtLoader,
    UnstructuredExcelLoader,
    PyMuPDFLoader,
)

logger = logging.getLogger(__name__)

EXTENSIONS_TO_LOADERS = {
    ".pdf": PyMuPDFLoader,
    ".xls": UnstructuredExcelLoader,
    ".docx": Docx2txtLoader,
    ".txt": TextLoader,
    ".md": TextLoader,
    ".csv": CSVLoader,
}

DEVICE = torch.device(
    "mps" if torch.backends.mps.is_available() else
    "cuda" if torch.cuda.is_available() else
    "cpu"
)

START_INDEXING = os.environ.get("START_INDEXING")
LOCAL_FILES_PATH = os.environ.get("LOCAL_FILES_PATH")
CONTAINER_PATH = "/usr/src/app/local_files/"

class Indexer:

    def __init__(self):
        self.qdrant = QdrantClient(
            host=os.environ.get("QDRANT_BOOTSTRAP"), 
        )
        embed_model_id = os.environ.get("EMBEDDING_MODEL_ID")
        self.embed_model = HuggingFaceEmbeddings(
            model_name=embed_model_id,
            model_kwargs={'device': DEVICE},
            encode_kwargs={'normalize_embeddings': False}
        )
        file_collection = os.environ.get("QDRANT_COLLECTION")
        self.document_store = self.setup_collection(file_collection)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500, 
            chunk_overlap=200
        )

    def setup_collection(self, collection_name):
        embedding_size = os.environ.get("EMBEDDING_SIZE")
        if not self.qdrant.collection_exists(collection_name):
            self.qdrant.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=embedding_size, 
                    distance=Distance.COSINE
                ),
            )
        return QdrantVectorStore(
            client=self.qdrant,
            collection_name=collection_name,
            embedding=self.embed_model,
        )
    
    def _create_loader(self, file_path):
        file_extension = file_path[file_path.rfind("."):].lower()
        loader_class = EXTENSIONS_TO_LOADERS.get(file_extension)
        if loader_class:
            return loader_class(file_path=file_path)
        raise ValueError(f"Unsupported file type: {file_extension}")
    
    def _process_file(self, loader):
        try:
            documents = loader.load_and_split(self.text_splitter)
            logger.info(f"Loaded {len(documents)} documents.")
            uuids = (str(uuid.uuid4()) for _ in range(len(documents)))
            ids = self.document_store.add_documents(documents=documents, ids=list(uuids))
            logger.info(f"Successfully added {len(ids)} documents.")
            return ids
        except Exception as e:
            logger.error(f"Error: {e}")
            return []

    def index(self, message):
        path, file_id = message["path"], message["file_id"]
        logger.info(f"Extracting text from file: {path} with id: {file_id}")
        try:
            loader = self._create_loader(path)
            ids = self._process_file(loader)
            logger.info(f"Inserted into vector storage: {path} with ids: {ids}")
        except Exception as e:
            logger.error(f"Failed process: {getattr(loader, 'file_path', 'unknown file')}")

    def find(self, query):
        try:
            logger.info(f"Searching for query: {query}")
            found = self.document_store.search(query, search_type="similarity")
            logger.info(f"Found {len(found)} results for query: {query}")
            links = set()
            result = ''
            for item in found:
                logger.info(f"Found item: {item}")
                path = item.metadata["file_path"].replace(CONTAINER_PATH, LOCAL_FILES_PATH)
                path = f"file://{path}"
                links.add(path)
                result = f"{result}. {item.page_content}" if result else item.page_content
            output = {
                "links": links,
                "output": result
            }
            logger.info(f"Returning output: {output}")
            return output
        except Exception as e:
            logger.error(f"Failed to search: {e}")
            return {"result":'Unabe to find anything for the given query'}