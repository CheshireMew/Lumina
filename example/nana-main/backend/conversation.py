from typing import List
import chromadb
from chromadb.config import Settings
from chromadb.api.types import EmbeddingFunction
from datetime import datetime
import uuid
from embedding import EmbeddingService
from config import Config

class APIEmbeddingFunction(EmbeddingFunction):
    def __init__(self):
        self.embedding_service = EmbeddingService(
            api_key=Config.EMBEDDING_API_KEY,
            api_url=Config.EMBEDDING_API_URL,
            model=Config.EMBEDDING_MODEL,
            dimension=Config.EMBEDDING_DIMENSION
        )
        
    def __call__(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        for text in texts:
            try:
                embedding = self.embedding_service.get_embedding(text)
                if embedding is None:
                    embedding = [0.0] * Config.EMBEDDING_DIMENSION
                embeddings.append(embedding)
            except Exception as e:
                print(f"获取embedding时出错喵: {e}")
                embedding = [0.0] * Config.EMBEDDING_DIMENSION
                embeddings.append(embedding)
        return embeddings


class ConversationTurn:
    def __init__(self, ask: str, answer: str):
        self.ask = ask
        self.answer = answer

    def __str__(self):
        return f"user: {self.ask}\nassistant: {self.answer}"


class ConversationHistory:
    def __init__(self, max_turns: int = 20):
        self.turns = []
        self.max_turns = max_turns

        # 初始化向量数据库客户端
        self.client = chromadb.Client(Settings(
            persist_directory="save/memory",
            is_persistent=True
        ))
        
        # 获取或创建集合
        self.collection = self.client.get_or_create_collection(
            name="memory",
            embedding_function=APIEmbeddingFunction()
        )
        
    def add_dialog(self, user_message: str, assistant_message: str):
        """添加新对话，并在需要时触发自动归档"""
        turn = ConversationTurn(user_message, assistant_message)
        self.turns.append(turn)
        
        # 当对话数量达到最大值时，自动归档一半的对话
        if len(self.turns) >= self.max_turns:
            self._auto_archive()
            
    def _auto_archive(self):
        """自动归档一半的对话"""
        if not self.turns:
            return
            
        # 计算要归档的对话数量
        archive_count = len(self.turns) // 2
        
        # 准备归档内容
        archive_turns = self.turns[:archive_count]
        content = "\n".join(str(turn) for turn in archive_turns)
        
        print("以下内容将被归档：")
        print(content)
        print("--------------------------------")
        
        # 保存到向量数据库
        self.collection.add(
            documents=[content],
            metadatas=[{
                "timestamp": datetime.now().isoformat()
            }],
            ids=[str(uuid.uuid4())]
        )
        
        # 移除已归档的对话
        self.turns = self.turns[archive_count:]
        
    def get_context(self) -> str:
        """获取格式化后的对话上下文"""
        return "\n".join(str(turn) for turn in self.turns)
        
    def retrieve(self, user_message: str, n_results: int = 3) -> List[str]:
        """获取与用户消息最相关的历史记忆"""
        results = self.collection.query(
            query_texts=[user_message],
            n_results=n_results,
            include=['documents']
        )
        
        return results['documents'][0] if results['documents'] else []


if __name__ == "__main__":
    async def main():
        conversation_history = ConversationHistory(max_turns=20)
        #conversation_history.add_dialog("广州有什么好吃的", "有烧鹅")
        #conversation_history.add_dialog("最近有什么电影看", "有流浪地球2")
        
        # 使用 await 调用异步方法
        #await conversation_history.archive(1, 1, "电影推荐")
        #await conversation_history.archive(0, 0, "广州有什么好吃的")
        
        memories = conversation_history.retrieve("广州美食", n_results=1)
        print("--------------------------------")
        print(memories)

    # 运行异步主函数
    asyncio.run(main())

