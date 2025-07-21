# filepath: langchain-agent/src/agents/base_agent.py
from langchain.agents import Tool, AgentExecutor, LLMSingleActionAgent
from langchain.memory import ConversationBufferMemory

class BaseAgent:
    def __init__(self, llm):
        self.llm = llm
        self.memory = ConversationBufferMemory(memory_key="chat_history")
        
    def add_tool(self, tool):
        """Add a tool to the agent's toolkit"""
        if not hasattr(self, 'tools'):
            self.tools = []
        self.tools.append(tool)
    
    def initialize(self):
        """Initialize the agent with tools and memory"""
        pass
    
    async def run(self, input_text):
        """Run the agent with given input"""
        pass