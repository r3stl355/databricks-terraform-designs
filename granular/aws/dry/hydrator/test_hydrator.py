import unittest
from hydrator import TerragruntConfigParser
import os

class TestHydrator(unittest.TestCase):

    def setUp(self):
        self.config = TerragruntConfigParser('/tmp/non-file.hcl', config_str='', required_blocks=[])

    def test_get_env(self):
        key = 'hydrator_test_get_env_key'
        val = 'test_my_env'
        os.environ[key] = val
        is_ok, res = self.config._resolve(f'"${{get_env("{key}")}}"')
        self.assertTrue(is_ok)
        self.assertEqual(res, val)


if __name__ == '__main__':
    unittest.main()