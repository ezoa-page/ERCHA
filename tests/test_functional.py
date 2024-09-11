import unittest
import os
import logging
import sys
from io import BytesIO

# Dynamically add the root directory of the project to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, root_dir)

from ercha.rch import RCH, ENCODING_BZIP2, ENCODING_XOR255_LZW, ENCODING_XOR255

class TestRCH(unittest.TestCase):

    def setUp(self):
        # Set up logging
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        self.logger.info("Setting up the test environment.")
        self.test_data = b'This is a test data for RCH.'
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

    def test_pack_rch(self):
        self.logger.info("Testing RCH pack_rch method.")
        try:
            result = self.rch_handler.pack_rch(self.test_rch_file, [self.test_filename])
            self.logger.debug(f"Pack result: {result}")
            self.assertEqual(result[0]['status'], 'Packed')
            self.assertTrue(os.path.exists(self.test_rch_file))
        except Exception as e:
            self.logger.error(f"Error during test_pack_rch: {e}")
            self.fail(f"Exception raised in test_pack_rch: {e}")

    def test_unpack_rch(self):
        self.logger.info("Testing RCH unpack_rch method.")
        try:
            self.rch_handler.pack_rch(self.test_rch_file, [self.test_filename])
            result = self.rch_handler.unpack_rch(self.test_rch_file, self.test_output_dir)
            self.logger.debug(f"Unpack result: {result}")
            self.assertEqual(result[0]['status'], 'Unpacked')
            unpacked_file_path = os.path.join(self.test_output_dir, self.test_filename)
            self.assertTrue(os.path.exists(unpacked_file_path))
            with open(unpacked_file_path, 'rb') as f:
                unpacked_data = f.read()
            self.assertEqual(unpacked_data, self.test_data)
        except Exception as e:
            self.logger.error(f"Error during test_unpack_rch: {e}")
            self.fail(f"Exception raised in test_unpack_rch: {e}")

    def test_check_crc(self):
        self.logger.info("Testing RCH check_crc method.")
        try:
            self.rch_handler.pack_rch(self.test_rch_file, [self.test_filename])
            result = self.rch_handler.check_rch(self.test_rch_file)
            self.logger.debug(f"CRC check result: {result}")
            self.assertTrue(result[0]['crc_passed'])
        except Exception as e:
            self.logger.error(f"Error during test_check_crc: {e}")
            self.fail(f"Exception raised in test_check_crc: {e}")

    def test_encoding_algorithms(self):
        self.logger.info("Testing RCH with different compression algorithms.")
        try:
            self.rch_handler.encoding_algorithm = ENCODING_BZIP2
            result = self.rch_handler.pack_rch(self.test_rch_file, [self.test_filename])
            self.logger.debug(f"Compression BZIP2 result: {result}")
            self.assertEqual(result[0]['encoding'], 'BZIP2')

            self.rch_handler.encoding_algorithm = ENCODING_XOR255_LZW
            result = self.rch_handler.pack_rch(self.test_rch_file, [self.test_filename])
            self.logger.debug(f"Compression XOR255+LZW result: {result}")
            self.assertEqual(result[0]['encoding'], 'XOR255+LZW')

            self.rch_handler.encoding_algorithm = ENCODING_XOR255
            result = self.rch_handler.pack_rch(self.test_rch_file, [self.test_filename])
            self.logger.debug(f"Compression XOR255 result: {result}")
            self.assertEqual(result[0]['encoding'], 'XOR255')
        except Exception as e:
            self.logger.error(f"Error during test_encoding_algorithms: {e}")
            self.fail(f"Exception raised in test_encoding_algorithms: {e}")

    def test_xor255_function(self):
        self.logger.info("Testing RCH xor255 function.")
        try:
            original_data = b'hello world'
            xor_data = self.rch_handler.xor255(original_data)
            self.logger.debug(f"XOR data: {xor_data}")
            self.assertNotEqual(original_data, xor_data)
            unxor_data = self.rch_handler.xor255(xor_data)
            self.logger.debug(f"UnXOR data: {unxor_data}")
            self.assertEqual(original_data, unxor_data)
        except Exception as e:
            self.logger.error(f"Error during test_xor255_function: {e}")
            self.fail(f"Exception raised in test_xor255_function: {e}")

    def test_detract_files(self):
        self.logger.info("Testing RCH detract_files method.")
        try:
            # Pack the archive with multiple files
            files_to_pack = [self.test_filename, 'additional_file.txt']
            with open('additional_file.txt', 'wb') as f:
                f.write(b'Additional file content.')
            self.rch_handler.pack_rch(self.test_rch_file, files_to_pack)

            # Attempt to detract files
            files_to_remove = [self.test_filename, 'non_existent_file.txt']
            removed_files, not_removed_files = self.rch_handler.detract_files(self.test_rch_file, files_to_remove)

            self.logger.debug(f"Removed files: {removed_files}")
            self.logger.debug(f"Not removed files: {not_removed_files}")

            # Assertions
            self.assertIn(self.test_filename, removed_files)
            self.assertIn('non_existent_file.txt', not_removed_files)
            self.assertNotIn(self.test_filename, not_removed_files)
            self.assertNotIn('non_existent_file.txt', removed_files)
        except Exception as e:
            self.logger.error(f"Error during test_detract_files: {e}")
            self.fail(f"Exception raised in test_detract_files: {e}")

        finally:
            # Clean up additional file
            if os.path.exists('additional_file.txt'):
                os.remove('additional_file.txt')

if __name__ == '__main__':
    unittest.main()
