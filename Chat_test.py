import unittest
from CheckSum import checksum


class MyTestCase(unittest.TestCase):
    def test_checksum(self):
        msg1 = "Hello world"
        msg2 = "Hello World"
        self.assertNotEqual(checksum(msg1), checksum(msg2))
        self.assertEqual(checksum(msg1), checksum(msg1))  # add assertion heree


# Cannot test the rest of the functions because it required a running server and a running client.
# all the function are based on the connection we couldn't find a way to run the server and the client at the same time with the test unit to test all the function.

if __name__ == '__main__':
    unittest.main()
