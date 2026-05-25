from langchain_chroma import Chroma
from utils.config_handler import chroma_conf
from model.factory import embed_model
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os
from utils.path import get_abs_path
from utils.file_handler import get_file_md5_hex, pdf_loader,txt_loader,listdir_with_allowed_type
from utils.logger_handler import logger
from langchain_core.documents import Document

class VectorStoreService:
    def __init__(self):
        self.vector_store = Chroma(
            collection_name=chroma_conf["collection_name"],
            embedding_function=embed_model,
            persist_directory=chroma_conf["persist_directory"]
        )

        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size = chroma_conf["chunk_size"],
            chunk_overlap = chroma_conf["chunk_overlap"],
            separators=chroma_conf["separators"],
            length_function=len
        )

    def get_retriver(self):
        return self.vector_store.as_retriever(search_kwargs={"k": chroma_conf["k"]})
    
    def load_document(self):
        #从数据文件夹内读取数据文件，转为向量存入数据库，要计算文件的MD5做去重
        def check_md5_hex(md5_for_check):
            md5_file = get_abs_path(chroma_conf["md5_hex_store"])
            if not os.path.exists(md5_file):
                open(md5_file,"w",encoding="utf=8").close()
                return False
            
            with open(md5_file,"r",encoding="utf-8")as f:
                for line in f:
                    line = line.strip()
                    if line == md5_for_check:
                        return True
                    
                return False
            
        def save_md5_hex(md5_for_check:str):
            with open(get_abs_path(chroma_conf["md5_hex_store"]), "a", encoding="utf-8")as f:
                f.write(md5_for_check+"\n")

        def get_file_documents(read_path:str):
            if read_path.endswith("txt"):
                return txt_loader(read_path)
            if read_path.endswith("pdf"):
                return pdf_loader(read_path)
            
            return []
        
        path = get_abs_path(chroma_conf["data_path"])
        allowed_files_paths: list[str] = listdir_with_allowed_type(
            get_abs_path(chroma_conf["data_path"]),
            tuple(chroma_conf["allow_knowledge_file_type"])
        )

        for path in allowed_files_paths:
            md5_hex = get_file_md5_hex(path)
            if check_md5_hex(md5_hex):
                logger.info(f"[加载知识库]{path}内容已存在知识库内，跳过")
                continue
            try:
                documents: list[Document] = get_file_documents(path)
                if not documents:
                    logger.warning(f"[加载知识库]{path}内没有有效文本内容，跳过")
                    continue
                split_document:list[Document] = self.spliter.split_documents(documents)
                if not split_document:
                    logger.warning(f"[加载知识库]{path}分片后没有有效文本内容，跳过")
                    continue
                # 将内容存入向量库
                self.vector_store.add_documents(split_document)
                # 将md5写入文件，避免下次重复加载
                save_md5_hex(md5_hex)
                logger.info(f"[加载知识库]{path}内容加载成功")
            except Exception as e :
                # exc_info会记录详细的报错堆栈
                logger.error(f"[加载知识库]{path}加载失败：{str(e)}",exc_info=True)
                continue

# if __name__=='__main__':
#     vs = VectorStoreService()
#     vs.load_document()
#     retriver = vs.get_retriver()
#     res = retriver.invoke("1")
#     for r in res:
#         print(r.page_content)
#         print("="*20)