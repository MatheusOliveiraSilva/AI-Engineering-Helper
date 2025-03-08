# AI-Engineering-Helper

## Repository goal
This repository is a side project that i made to create a chatbot from scrath and send it to production.
I have built several chatbots in the past, 

Repository to test my skills, since prototype to production. I have built several chatbots for companies i worked for, but i never had the opportunity to build one from scratch and send it to production by myself.

Today i have some doubts like: How to use to create a pipeline to deploy a chatbot? How to monitor, scale and serve for multiple users? How to store chat history? Tha'ts some stuff i'll find out in this repository.

## Project Initialization Steps:
1. First I will create our llm_configuration file, that will use our parameters such as model_name, provider and return a LLM instanced. That is specially useful for cases that we want to create a chat bot with a buttom that allow user to change the model (that will be a feature in future).
2. I will need to create a preprocessment module, that contain:
    1. A embedding configuration file, that will contain the parameters to create the embedding model. For same reason we have a llm_configuration file, we will have a embedding_configuration file.
    2. A chunking module, that will receive a text and return a list of chunks. We need to build a module because we can decide to change the chunking strategie in future, so we need to keep this module isolated. For now, based on the fact that our documents are all pdfs such papers, books sessions and blog posts, we will use a content-aware chunking strategie, that break the text in chunks based on the content of the text, not just after a fixed number of tokens such as fized-sized chunking strategy.
    3. Create a module to augment our chunks if we want any preprocessment technique. I this case i'm applying a proprocessment technique called contextual embedding, that you can read more about in this [link](https://www.anthropic.com/news/contextual-retrieval07820), so our preprocessment pipeline is: chunking -> augment chunks -> embedding.
3. We need to have a module to manage our vector database, this need to be created before third item of last step. I decided to use Pinecone as our vector database, because i decided to use HybridSearch as our documents retriever, and pinecone have a good integration with HybridSearch using langchain, you can see in link [here](https://python.langchain.com/docs/integrations/retrievers/pinecone_hybrid_search/). I we need to create 3 classes in this module:
    1. First class is a Pinecone utility class, that given an ```index_name``` we check if the index exists. If exists, we use the index, if don't exist we create the index and have methods that helps us to insert documents in that index. That follows a convention that says the index configuration, for example:
    ```python
    pinecone_utils = PineconeUtils(
        # This index on test is the index used in this project, the name is a abreviation of:
        # 1. context aware chunked
        # 2. contextual embeddings documents
        # 3. dot product similarity
        # 4. embedded with text-embedding-3-large embedding model
        index_name="ca-contextualemb-dotp-3large",
        embedding_model_name="text-embedding-3-large",
        embedding_provider="openai",
        metric="dotproduct"
    )
    ```
   2. After we have have a class that manage our index the configuration, we need to have a class that is the documents ingestion pipeline. This class will instance our content-aware chunker, preprocess the chunks to make contextual embedding and after all this we create a uuid for each chunk and insert in Pinecone.
   3. The last class is the hybrid retrieval class, to make a hybrid search we need a sparse and dense enconder. The sparse encoder is created using our corpus (all textual information about our chunked documents) and when i instance the hybrid retriever, i need to pass the sparse enconder as a parameter, so to instance it i ingest all the corpus and fit the BM25 encoder td-if values in the corpus.

## Building agent back and front end.
For more details about how i created the agent using [LangGraph](https://www.langchain.com/langgraph) and the steps i followed to create it, you can see the [agent documentation](./chatbot/README.md).

To integrate the application with the front end, i used the [Streamlit](https://streamlit.io/) library, that is a library that allows you to create web applications using python. I created a simple web application that allows the user to interact with the chatbot, you can see the code in the [main_page.py](./front_end/main_page.py) file.

Also i created an API that front end call when is managing user chat histories, login sessions using [Auth0](https://auth0.com/?) and other log/monitoring stuff.

## Deploying the application

TODO 

## Running the app locally:

To run the app locally, you need to run:

```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

This ```install.sh``` script will:
1. Install requirements.txt
2. Download documents that i used on this chatbot via DropBox
3. Download bm25 encoder weights that i used for the sparse encoder in Hybrid Search -> TODO

