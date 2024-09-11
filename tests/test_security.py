import unittest
import os
import sys
import zlib  # Import zlib for CRC computation
import struct  # Import struct for binary data packing
import logging
import bz2  # Import bz2 for compression
from io import BytesIO

# Dynamically add the root directory of the project to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, root_dir)

from ercha.rch import RCH, ENCODING_BZIP2, ENCODING_XOR255_LZW, ENCODING_XOR255

class TestRCHSecurity(unittest.TestCase):

    def setUp(self):
        # Set up logging
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        self.logger.info("Setting up the test environment.")
        self.test_data = b'Some test data for security testing.'
        self.rch_handler = RCH(encoding_algorithm=ENCODING_BZIP2, compression_level=9)
        self.test_filename = 'test_file.txt'
        self.test_output_dir = 'test_output'
        self.test_rch_file = 'test_archive.rch'
        os.makedirs(self.test_output_dir, exist_ok=True)
        with open(self.test_filename, 'wb') as f:
            f.write(self.test_data)
        self.logger.info("Test environment setup complete.")

    def tearDown(self):
        self.logger.info("Tearing down the test environment.")
        if os.path.exists(self.test_filename):
            os.remove(self.test_filename)
        if os.path.exists(self.test_output_dir):
            for file in os.listdir(self.test_output_dir):
                os.remove(os.path.join(self.test_output_dir, file))
            os.rmdir(self.test_output_dir)
        if os.path.exists(self.test_rch_file):
            os.remove(self.test_rch_file)
        self.logger.info("Test environment teardown complete.")

    def test_unpack_path_traversal(self):
        """Test that path traversal attempts are sanitized."""
        self.logger.info("Testing path traversal prevention during unpacking.")
        dangerous_filename = '../dangerous_file.txt'
        safe_filename = 'dangerous_file.txt'
        try:
            compressed_test_data = bz2.compress(self.test_data)
            crc32_value = zlib.crc32(self.test_data)

            with open(self.test_rch_file, 'wb') as f:
                f.write(b'FR01')  # RCH_MAGIC
                f.write(b'\x01\x00\x00\x00')  # Version
                f.write(b'\x00\x00\x00\x00')  # Creation timestamp
                f.write(b'\x00' * 16)  # Reserved
                f.write(b'FZ')  # BLOCK_MAGIC
                f.write(dangerous_filename.ljust(40, '\x00').encode('utf-8'))
                f.write(struct.pack('<I I I I I', 1, 0, len(compressed_test_data), crc32_value, ENCODING_BZIP2))
                f.write(compressed_test_data)

            results = self.rch_handler.unpack_rch(self.test_rch_file, self.test_output_dir)
            self.logger.debug(f"Unpack results: {results}")
            self.assertIn(safe_filename, [result['filename'] for result in results], "Sanitized filename should be in results.")
            self.assertTrue(any(result['status'] == 'Unpacked' for result in results if result['filename'] == safe_filename), "Sanitized file should be unpacked successfully.")
        except Exception as e:
            self.logger.error(f"Error during test_unpack_path_traversal: {e}")
            self.fail(f"Exception raised in test_unpack_path_traversal: {e}")

    def test_unpack_invalid_file(self):
        """Test that invalid RCH file format is handled correctly."""
        self.logger.info("Testing handling of invalid RCH file format.")
        try:
            with open(self.test_rch_file, 'wb') as f:
                f.write(b'INVALIDHEADER')  # Invalid header
            with self.assertRaises(ValueError) as context:
                self.rch_handler.unpack_rch(self.test_rch_file, self.test_output_dir)
            self.logger.debug(f"Expected ValueError raised: {context.exception}")
            self.assertIn("Invalid RCH file format", str(context.exception))
        except Exception as e:
            self.logger.error(f"Error during test_unpack_invalid_file: {e}")
            self.fail(f"Exception raised in test_unpack_invalid_file: {e}")

    def test_unpack_corrupted_data(self):
        """Test that corrupted data is handled correctly."""
        self.logger.info("Testing handling of corrupted data during unpacking.")
        try:
            corrupted_data = b'corrupted_data'
            with open(self.test_rch_file, 'wb') as f:
                f.write(b'FR01')  # RCH_MAGIC
                f.write(b'\x01\x00\x00\x00')  # Version
                f.write(b'\x00\x00\x00\x00')  # Creation timestamp
                f.write(b'\x00' * 16)  # Reserved
                f.write(b'FZ')  # BLOCK_MAGIC
                f.write(self.test_filename.ljust(40, '\x00').encode('utf-8'))
                f.write(struct.pack('<I I I I I', 1, 0, len(corrupted_data), zlib.crc32(corrupted_data), ENCODING_BZIP2))
                f.write(corrupted_data)

            results = self.rch_handler.unpack_rch(self.test_rch_file, self.test_output_dir)
            self.logger.debug(f"Unpack results: {results}")
            self.assertFalse(any(result['crc_passed'] for result in results), "CRC check should fail for corrupted data.")
            self.assertTrue(any(result['status'] == 'Failed' for result in results), "File should fail to unpack correctly due to corrupted data.")
        except Exception as e:
            self.logger.error(f"Error during test_unpack_corrupted_data: {e}")
            self.fail(f"Exception raised in test_unpack_corrupted_data: {e}")

    def test_crc_mismatch(self):
        """Test that CRC mismatches are detected."""
        self.logger.info("Testing detection of CRC mismatches.")
        try:
            mismatched_data = b'data_with_wrong_crc'
            correct_crc = zlib.crc32(b'correct_data')  # Correct CRC based on different data
            with open(self.test_rch_file, 'wb') as f:
                f.write(b'FR01')  # RCH_MAGIC
                f.write(b'\x01\x00\x00\x00')  # Version
                f.write(b'\x00\x00\x00\x00')  # Creation timestamp
                f.write(b'\x00' * 16)  # Reserved
                f.write(b'FZ')  # BLOCK_MAGIC
                f.write(self.test_filename.ljust(40, '\x00').encode('utf-8'))
                f.write(struct.pack('<I I I I I', 1, 0, len(mismatched_data), correct_crc, ENCODING_BZIP2))
                f.write(mismatched_data)

            results = self.rch_handler.check_rch(self.test_rch_file)
            self.logger.debug(f"CRC check results: {results}")
            self.assertFalse(results[0]['crc_passed'], "CRC mismatch should be detected and flagged in the results.")
        except Exception as e:
            self.logger.error(f"Error during test_crc_mismatch: {e}")
            self.fail(f"Exception raised in test_crc_mismatch: {e}")

    def test_malformed_file_handling(self):
        """Test that malformed file data is handled properly."""
        self.logger.info("Testing handling of malformed file data.")
        try:
            malformed_data = b'malformed_data'
            with open(self.test_rch_file, 'wb') as f:
                f.write(b'FR01')  # RCH_MAGIC
                f.write(b'\x01\x00\x00\x00')  # Version
                f.write(b'\x00\x00\x00\x00')  # Creation timestamp
                f.write(b'\x00' * 16)  # Reserved
                f.write(b'FZ')  # BLOCK_MAGIC
                f.write(self.test_filename.ljust(40, '\x00').encode('utf-8'))
                f.write(struct.pack('<I I I I I', 1, 0, len(malformed_data), zlib.crc32(malformed_data), ENCODING_XOR255_LZW))
                f.write(malformed_data)

            results = self.rch_handler.unpack_rch(self.test_rch_file, self.test_output_dir)
            self.logger.debug(f"Unpack results: {results}")
            self.assertFalse(any(result['crc_passed'] for result in results), "CRC check should fail for malformed data.")
            self.assertTrue(any(result['status'] == 'Failed' for result in results), "File should fail to unpack correctly due to malformed data.")
        except Exception as e:
            self.logger.error(f"Error during test_malformed_file_handling: {e}")
            self.fail(f"Exception raised in test_malformed_file_handling: {e}")

if __name__ == '__main__':
    unittest.main()
