To use the `paraphrase-multilingual-mpnet-base-v2` embedding model with `pgvector` in PostgreSQL using LlamaIndex in Python, you'll need to configure LlamaIndex to use a local embedding model and a PostgreSQL vector store.

Here's a step-by-step guide:

### 1\. Prerequisites 💻

First, make sure you have a running PostgreSQL instance with the `pgvector` extension installed. You'll also need the necessary Python libraries.

```bash
pip install llama-index-vector-stores-postgres
pip install llama-index-embeddings-huggingface
pip install psycopg2-binary
pip install "sentence-transformers>=2.0.0"
```

The `llama-index-embeddings-huggingface` library provides the `HuggingFaceEmbedding` class, which is how LlamaIndex integrates with models from the Hugging Face Hub, including your chosen model.

-----

### 2\. Setting Up the Database Connection 🔌

You'll need to create a connection to your PostgreSQL database. This involves defining the connection string and setting up the `PGVectorStore` object.

```python
import psycopg2
from sqlalchemy import make_url
from llama_index.vector_stores.postgres import PGVectorStore

# Define your database connection details
db_name = "vector_db"
user = "postgres"
password = "your_password"
host = "localhost"
port = "5432"

# Create a connection to the database
connection_string = f"postgresql://{user}:{password}@{host}:{port}"
conn = psycopg2.connect(connection_string)
conn.autocommit = True

# Drop and create the database for a fresh start
with conn.cursor() as c:
    c.execute(f"DROP DATABASE IF EXISTS {db_name}")
    c.execute(f"CREATE DATABASE {db_name}")

# Create the PGVectorStore object
vector_store = PGVectorStore.from_params(
    database=db_name,
    host=host,
    password=password,
    port=port,
    user=user,
    table_name="your_table_name",
    # The 'paraphrase-multilingual-mpnet-base-v2' model has 768 dimensions
    embed_dim=768
)
```

The `embed_dim` parameter is crucial here; it must match the output dimension of your embedding model, which for `paraphrase-multilingual-mpnet-base-v2` is **768**.

-----

### 3\. Configuring the Embedding Model 🤖

Next, you'll instantiate your embedding model. This is where you specify `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` using the `HuggingFaceEmbedding` class from LlamaIndex.

```python
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Settings

# Set the embedding model globally
Settings.embed_model = HuggingFaceEmbedding(
    model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
)
```

Setting the model in `Settings` ensures that it's used by default throughout your LlamaIndex application for both document ingestion and query embedding.

-----

### 4\. Indexing and Querying Data 🔎

With the vector store and embedding model configured, you can now load your documents, create an index, and perform queries.

```python
from llama_index.core import SimpleDirectoryReader, StorageContext, VectorStoreIndex

# Load your documents
documents = SimpleDirectoryReader("path/to/your/data").load_data()

# Create a storage context with the vector store
storage_context = StorageContext.from_defaults(vector_store=vector_store)

# Create the index from your documents
index = VectorStoreIndex.from_documents(
    documents,
    storage_context=storage_context
)

# Create a query engine and run a query
query_engine = index.as_query_engine()
response = query_engine.query("Your query here")
print(response)
```

When you create the index, LlamaIndex automatically uses the `HuggingFaceEmbedding` model you set in `Settings` to generate and store the 768-dimensional vector embeddings in your `pgvector` table. Similarly, when you query, the model will embed your query and perform a semantic search in PostgreSQL.