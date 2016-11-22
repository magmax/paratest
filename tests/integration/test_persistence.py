import os
import unittest
from paratest.persistence import Persistence


class PersistenceTest(unittest.TestCase):
    db_file = 'test.db'

    def setUp(self):
        if os.path.exists(self.db_file):
            os.remove(self.db_file)
        self.sut = Persistence(self.db_file, 'TEST')

    def test_initialize(self):
        self.sut.initialize()
        assert os.path.exists(self.db_file)
