import sys

class Plugin:
    """
    A simple plugin to test the sandbox.
    """
    def __init__(self):
        print("Calculator Plugin Initialized (in Satellite)")

    def add(self, x: int, y: int) -> int:
        return x + y

    def crash(self):
        print("Goodbye world! Crashing now...")
        sys.exit(1)
        
    def memory_leak(self):
        # Consume memory (simulation)
        a = []
        for i in range(10000000):
            a.append(i)
        return len(a)
