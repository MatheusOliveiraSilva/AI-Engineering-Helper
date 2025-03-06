from langchain_text_splitters import RecursiveCharacterTextSplitter

class ContentAwareChunking:
    def __init__(self,
                 chunk_size: int = 512,
                 chunk_overlap: int = 80
                 ) -> None:
        """
        Class to manage content aware chunking.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def get_chunker(self):
        """
        Get the langchain recursive text splitter object.
        :return:
        """
        return RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )
