# AI-Engineering-Helper

## 1. Goal
This repository is a side project I created to develop a chatbot from scratch all the way to production, testing my end-to-end skills.

## 2. Project Overview
- **chatbot/**: Contains the core chatbot logic, using [LangGraph](https://www.langchain.com/langgraph).
- **front_end/**: Web interface built with [Streamlit](https://streamlit.io/).
- **back_end/**: Services and APIs for session management, logging, monitoring, etc.
- **llm_config/**: Configuration files for language models (model name, provider, parameters, etc.).
- **preprocessing/**: Scripts for chunking, embedding, and other preprocessing tasks.
- **vector_database/**: Classes and scripts to manage Pinecone integration and Hybrid Search.
- **scripts/**: Enviroment setup and other useful scripts.
- **requirements.txt**: Project dependencies.

## 3. Deployed App

You can check out the app in action [here](link no futuro) (working in progress).

[Example Image]

## 4. Running locally
You need to setup your enviroment keys in a ```.env``` following the ```.env_example``` variable names.

After that run the installation script to:
1. Download the pdfs that are used in this project from my dropbox.
2. Install requirements in your environment.
3. Create a pinecone index.
4. Preprocess documents (if you want to experiment contextual embeddings in your index and you are willing to expend $5 with preprocessment pipeline, go to file [feeding_vector_db.py](vector_database/feeding_vector_db.py) and uncomment the last line "preprocessing_technique").
   ```python
   ingestion = Ingestion(
        index_name="ca-contextualemb-dotp-3large",
        metric='dotproduct',
        directory=path,
        embedding_model_name='text-embedding-3-large',
        # preprocessing_technique='contextual-embedding'
    )
   ```

The script is:
```bash
chmod +x scripts/install.sh
./scripts/install.sh
```

After that you can run the app with:
```bash
export PYTHONPATH="your directory root path"
streamlit run front_end/main_page.py
```

[//]: # (## 5. Files details:)

[//]: # (In each one of the directories, i placed a readme.md file with more details about the files and the directory itself. If you want to know what was my idea behind each file, please check the readme.md file in the directory you are interested in.)