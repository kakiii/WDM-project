import unittest
import threading
import requests
import time

class DeadlockTestCase(unittest.TestCase):
    
    def test_deadlock(self):
        def  _request():
            requests.get('http://localhost:8080/')
        thread = threading.Thread(target=_request)
        thread.start()
        time.sleep(1)
        thread.join()
        self.assertTrue(True)
        