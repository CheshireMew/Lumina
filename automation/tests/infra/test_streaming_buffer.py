
import sys
import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock

# Mock Service Imports if possible, or just test the logic logic isolation
# Since ChatTurnService has pipeline dependencies, we might want to extract the buffering logic
# or mock the dependencies heavily.
# Alternatively, we can just test the generator logic if we refactor it into a helper.

# Strategy: Create a standalone generator function that mimics the logic to test it in isolation,
# OR verifying the logic inline in the test if we implement it as a helper static method.
# For robustness, let's assume we will refactor the yielding logic into a helper method `_buffered_yield`
# in ChatTurnService, or just test it via a dummy service subclass.

class MockDriver:
    def __init__(self, chunks):
        self.chunks = chunks

    async def chat_completion(self, *args, **kwargs):
        for c in self.chunks:
            yield c
            await asyncio.sleep(0.01) # Simulate delay

class TestStreamingBuffer(unittest.TestCase):
    def setUp(self):
        pass

    async def _consume_stream(self, stream):
        results = []
        async for chunk in stream:
            results.append(chunk)
        return results

    def test_buffering_logic(self):
        """test manual logic if we extract it, or E2E if we mock full service"""
        # Since running full service test is complex, let's verify the ALGORITHM here 
        # that we are about to put into chat_service.py.
        
        async def mock_stream_logic(source_chunks):
            buffer = ""
            results = []
            
            async for chunk in source_chunks:
                buffer += chunk
                
                # Logic to be implemented:
                while True:
                    # Check for newline
                    newline_idx = buffer.find("\n")
                    # Check for sentence endings (heuristic: ". ", "? ", "! ")
                    # Finding the *earliest* delimiter
                    delimiters = [
                        (buffer.find("\n"), 1), 
                        (buffer.find(". "), 2), 
                        (buffer.find("? "), 2), 
                        (buffer.find("! "), 2)
                    ]
                    # Filter not found (-1)
                    valid_delims = [(idx, length) for idx, length in delimiters if idx != -1]
                    
                    if not valid_delims:
                        break # No delimiter found
                        
                    # Find earliest
                    split_idx, split_len = min(valid_delims, key=lambda x: x[0])
                    
                    # Yield content INCLUDING the delimiter (to preserve structure)
                    # For . ? ! we might want to keep the space or not? 
                    # Usually "Hello. World" -> yields "Hello. " then "World"
                    
                    # The split point is at idx + length
                    cut_point = split_idx + split_len
                    
                    to_yield = buffer[:cut_point]
                    buffer = buffer[cut_point:]
                    results.append(to_yield)
                    
                # Safety valve: if buffer grows too large (e.g. code block without newline?)
                if len(buffer) > 100: # Threshold
                     results.append(buffer)
                     buffer = ""
                     
            if buffer:
                results.append(buffer)
                
            return results

        # Test Case 1: Simple Sentence
        async def run_test():
            # "Hello. " comes in tokens: ["Hel", "lo", ". ", "Wor", "ld"]
            chunks = ["Hel", "lo", ". ", "Wor", "ld"]
            
            async def chunk_gen():
                for c in chunks: yield c
            
            output = await mock_stream_logic(chunk_gen())
            # Expected: "Hello. " then "World"
            print(f"Output 1: {output}")
            assert output[0] == "Hello. "
            assert output[1] == "World"
            
            # Test Case 2: Newlines
            chunks2 = ["Line", "1\nLine", "2"]
            async def chunk_gen2():
                for c in chunks2: yield c
                
            output2 = await mock_stream_logic(chunk_gen2())
            # Expected: "Line1\n", "Line2"
            print(f"Output 2: {output2}")
            assert output2[0] == "Line1\n"
            assert output2[1] == "Line2"

        asyncio.run(run_test())

if __name__ == "__main__":
    test = TestStreamingBuffer()
    test.test_buffering_logic()
    print("✅ Buffer Logic Test Passed")
