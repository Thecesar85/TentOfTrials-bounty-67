import unittest
from config_generator import generate_config, merge_config, mask_sensitive, DEFAULT_CONFIG

class TestConfigGenerator(unittest.TestCase):
    def test_merge_config(self):
        base = {"a": {"b": 1, "c": 2}, "d": 3}
        override = {"a": {"c": 9}, "e": 4}
        result = merge_config(base, override)
        
        self.assertEqual(result["a"]["b"], 1)
        self.assertEqual(result["a"]["c"], 9)
        self.assertEqual(result["d"], 3)
        self.assertEqual(result["e"], 4)

    def test_generate_config(self):
        # Development
        dev_config = generate_config("development")
        self.assertEqual(dev_config["app"]["environment"], "development")
        self.assertTrue(dev_config["app"]["debug"])
        
        # Production
        prod_config = generate_config("production")
        self.assertEqual(prod_config["app"]["environment"], "production")
        self.assertFalse(prod_config["app"]["debug"])
        self.assertEqual(prod_config["database"]["pool_max"], 50)
        
    def test_mask_sensitive(self):
        config = generate_config("development")
        # Set some sensitive values manually for testing
        config["database"]["password"] = "supersecretDB"
        config["redis"]["password"] = "supersecretRedis"
        config["auth"]["jwt_secret"] = "supersecretJWT"
        
        masked = mask_sensitive(config)
        
        self.assertEqual(masked["database"]["password"], "***REDACTED***")
        self.assertEqual(masked["redis"]["password"], "***REDACTED***")
        self.assertEqual(masked["auth"]["jwt_secret"], "***REDACTED***")
        # Non sensitive stays same
        self.assertEqual(masked["database"]["user"], "tent_app")

if __name__ == '__main__':
    unittest.main()
