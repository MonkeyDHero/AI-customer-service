from rag.vector_store import VectorStoreService
from utils.prompt_loader import load_rag_prompts
from langchain_core.prompts import PromptTemplate
from model.factory import chat_model
from langchain_core.output_parsers import StrOutputParser

def print_prompt(prompt):
    print("="*20)
    print(prompt.to_string())
    print("="*20)
    return prompt

class RagSummarizeService(object):
    def __init__(self):
        self.vector_store = VectorStoreService()
        self.retriver = self.vector_store.get_retriver()
        self.prompt_text= load_rag_prompts()
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        self.model=chat_model
        self.chain=self._init_chain()

    def _init_chain(self):
        chain = self.prompt_template | print_prompt | self.model | StrOutputParser()
        return chain
    
    def retriver_docs(self, query:str):
        return self.retriver.invoke(query)

    def rag_summarize(self, query:str):
        context_docs = self.retriver_docs(query)
        context=""
        counter=0
        for doc in context_docs:
            counter+=1
            context+=f"[参考资料{counter}]:参考资料：{doc.page_content} | 参考元数据：{doc.metadata}\n"
        
        return self.chain.invoke(
            {
                "input":query,
                "context":context
            }
        )