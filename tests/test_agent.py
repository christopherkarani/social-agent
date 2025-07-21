import unittest
from src.agents.base_agent import BaseAgent

class TestBaseAgent(unittest.TestCase):
    def setUp(self):
        self.agent = BaseAgent(llm=None)  # Replace None with a mock LLM if needed

    def test_add_tool(self):
        tool = "test_tool"
        self.agent.add_tool(tool)
        self.assertIn(tool, self.agent.tools)

    def test_initialize(self):
        self.agent.initialize()
        # Add assertions based on what initialize should do

    async def test_run(self):
        input_text = "Test input"
        result = await self.agent.run(input_text)
        # Add assertions based on expected output

if __name__ == '__main__':
    unittest.main()