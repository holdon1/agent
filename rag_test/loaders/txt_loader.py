from rag_test.loaders.base_document import BaseDocument, Document


class TextDocumentLoader(BaseDocument):
    # 需要确定数据路径
    def __init__(self, path):
        self.path = path
    def load(self):
        with open(
                self.path,
                "r",
                encoding="utf-8"
        ) as f:
            text = f.read()

        return [
            Document(
                content=text,
                metadata={
                    "source": self.path,
                    "type": "markdown"
                }
            )
        ]

if __name__ == '__main__':
    txt_path = r"D:\Code\PycharmProjects\PythonProject\rag_test\knowledge.txt"
    text_document_loader = TextDocumentLoader(txt_path)
    print(text_document_loader.load())