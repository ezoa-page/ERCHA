import unittest
import os
import sys
import zlib  # Import zlib for CRC computation
import struct  # Import struct for binary data packing
import logging
from io import StringIO, BytesIO

# Dynamically add the root directory of the project to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.insert(0, root_dir)

from ercha.rch import RCH, ENCODING_BZIP2, ENCODING_XOR255_LZW, ENCODING_XOR255

class TestRCHAdditional(unittest.TestCase):

    def setUp(self):
        # Set up logging
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

        self.logger.info("Setting up the test environment.")
        self.test_data = b'Edge case test data for RCH.'
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

    def test_maximum_data_size(self):
        self.logger.info("Testing handling of maximum data size.")
        large_data = b'a' * 10**6
        large_filename = 'large_file.txt'
        try:
            with open(large_filename, 'wb') as f:
                f.write(large_data)
            self.rch_handler.pack_rch(self.test_rch_file, [large_filename])
            result = self.rch_handler.unpack_rch(self.test_rch_file, self.test_output_dir)
            self.logger.debug(f"Unpack results: {result}")
            self.assertTrue(os.path.exists(os.path.join(self.test_output_dir, large_filename)))
            with open(os.path.join(self.test_output_dir, large_filename), 'rb') as f:
                unpacked_data = f.read()
            self.assertEqual(unpacked_data, large_data)
        except Exception as e:
            self.logger.error(f"Error during test_maximum_data_size: {e}")
            self.fail(f"Exception raised in test_maximum_data_size: {e}")
        finally:
            os.remove(large_filename)

    def test_simultaneous_file_operations(self):
        self.logger.info("Testing simultaneous file operations.")
        filenames = ['file1.txt', 'file2.txt', 'file3.txt']
        try:
            for name in filenames:
                with open(name, 'wb') as f:
                    f.write(b'This is ' + name.encode())
            self.rch_handler.pack_rch(self.test_rch_file, filenames)
            result = self.rch_handler.unpack_rch(self.test_rch_file, self.test_output_dir)
            self.logger.debug(f"Unpack results: {result}")
            self.assertEqual(len(result), 3)
            for name in filenames:
                unpacked_file_path = os.path.join(self.test_output_dir, name)
                self.assertTrue(os.path.exists(unpacked_file_path))
                with open(unpacked_file_path, 'rb') as f:
                    self.assertEqual(f.read(), b'This is ' + name.encode())
        except Exception as e:
            self.logger.error(f"Error during test_simultaneous_file_operations: {e}")
            self.fail(f"Exception raised in test_simultaneous_file_operations: {e}")
        finally:
            for name in filenames:
                os.remove(name)

    def test_invalid_command_line_arguments(self):
        self.logger.info("Testing invalid command line arguments.")
        original_stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            with self.assertRaises(ValueError) as context:
                self.rch_handler.encoding_algorithm = 99
                self.rch_handler.pack_rch(self.test_rch_file, [self.test_filename])
            self.logger.debug(f"Expected ValueError raised: {context.exception}")
            self.assertIn("Unknown encoding algorithm", str(context.exception))
        except Exception as e:
            self.logger.error(f"Error during test_invalid_command_line_arguments: {e}")
            self.fail(f"Exception raised in test_invalid_command_line_arguments: {e}")
        finally:
            sys.stderr = original_stderr

    def test_crc_collision_handling(self):
        self.logger.info("Testing CRC collision handling.")
        file1 = b'first data block'
        file2 = b'second data block'
        fake_crc = zlib.crc32(file1)  # Using zlib for CRC
        filename1 = 'file1.txt'
        filename2 = 'file2.txt'
        try:
            with open(filename1, 'wb') as f:
                f.write(file1)
            with open(filename2, 'wb') as f:
                f.write(file2)
            self.rch_handler.pack_rch(self.test_rch_file, [filename1])
            self.rch_handler.pack_rch(self.test_rch_file, [filename2], append=True)
            with open(self.test_rch_file, 'r+b') as f:
                f.seek(-12, os.SEEK_END)
                f.write(struct.pack('<I', fake_crc))
            result = self.rch_handler.check_rch(self.test_rch_file)
            self.logger.debug(f"CRC check results: {result}")
            self.assertTrue(result[0]['crc_passed'])
            self.assertFalse(result[1]['crc_passed'])
        except Exception as e:
            self.logger.error(f"Error during test_crc_collision_handling: {e}")
            self.fail(f"Exception raised in test_crc_collision_handling: {e}")
        finally:
            os.remove(filename1)
            os.remove(filename2)

    def test_large_number_of_files(self):
        self.logger.info("Testing handling of a large number of files.")
        num_files = 100
        filenames = [f'file_{i}.txt' for i in range(num_files)]
        try:
            for filename in filenames:
                with open(filename, 'wb') as f:
                    f.write(self.test_data)
            self.rch_handler.pack_rch(self.test_rch_file, filenames)
            result = self.rch_handler.unpack_rch(self.test_rch_file, self.test_output_dir)
            self.logger.debug(f"Unpack results: {result}")
            self.assertEqual(len(result), num_files)
            for filename in filenames:
                unpacked_file_path = os.path.join(self.test_output_dir, filename)
                self.assertTrue(os.path.exists(unpacked_file_path))
        except Exception as e:
            self.logger.error(f"Error during test_large_number_of_files: {e}")
            self.fail(f"Exception raised in test_large_number_of_files: {e}")
        finally:
            for filename in filenames:
                os.remove(filename)

    def test_packing_from_stdin(self):
        self.logger.info("Testing packing from stdin.")
        input_data = b'This is data from stdin.'
        input_stream = BytesIO(input_data)
        output_filename = 'stdin_test.rch'
        original_stdin = sys.stdin
        sys.stdin = input_stream  # Use BytesIO for stdin
        try:
            if not hasattr(sys.stdin, 'buffer'):
                sys.stdin = type('FakeStdin', (object,), {'buffer': sys.stdin})()
            self.rch_handler.pack_rch(output_filename, ['-'])
            self.logger.debug(f"Packed data from stdin to {output_filename}")
            self.assertTrue(os.path.exists(output_filename))
            self.rch_handler.unpack_rch(output_filename, self.test_output_dir)
            unpacked_file_path = os.path.join(self.test_output_dir, 'stdin')
            self.assertTrue(os.path.exists(unpacked_file_path))
            with open(unpacked_file_path, 'rb') as f:
                unpacked_data = f.read()
            self.assertEqual(unpacked_data, input_data)
        except Exception as e:
            self.logger.error(f"Error during test_packing_from_stdin: {e}")
            self.fail(f"Exception raised in test_packing_from_stdin: {e}")
        finally:
            sys.stdin = original_stdin  # Restore original stdin
            if os.path.exists(output_filename):
                os.remove(output_filename)

def test_forceful_extraction_with_bad_crc(self):
    self.logger.info("Testing forceful extraction with a bad CRC.")
    corrupted_rch_filename = 'corrupted_archive.rch'
    extracted_dir = 'extracted_bad_crc'
    os.makedirs(extracted_dir, exist_ok=True)

    # Step 1: Create a valid RCH archive
    self.rch_handler.pack_rch(self.test_rch_file, [self.test_filename])

    # Step 2: Corrupt the CRC of the file in the archive
    with open(self.test_rch_file, 'rb') as f:
        rch_data = bytearray(f.read())

    # Assuming CRC is stored in the last 4 bytes of each file block for simplicity
    if len(rch_data) > 4:
        rch_data[-4:] = b'\x00\x00\x00\x00'  # Overwriting CRC with zeroes

    # Write the corrupted archive to a new file
    with open(corrupted_rch_filename, 'wb') as f:
        f.write(rch_data)

    # Step 3: Attempt to extract the file with force=True
    try:
        self.rch_handler.force = True  # Enable force extraction
        self.logger.info(f"Force flag is set to: {self.rch_handler.force}")

        extracted_file_path = os.path.join(extracted_dir, self.test_filename)
        self.logger.info(f"Expected extracted file path: {extracted_file_path}")

        self.rch_handler.unpack_rch(corrupted_rch_filename, extracted_dir)

        # Check if the file was extracted
        file_exists = os.path.exists(extracted_file_path)
        self.logger.info(f"File extraction result: {file_exists}")

        self.assertTrue(file_exists, "File was not extracted forcefully despite bad CRC.")
        self.logger.info("Forceful extraction with bad CRC succeeded.")
    except Exception as e:
        self.logger.error(f"Forceful extraction with bad CRC failed: {str(e)}")
        self.fail(f"Forceful extraction with bad CRC failed: {str(e)}")
    finally:
        # Cleanup
        if os.path.exists(corrupted_rch_filename):
            os.remove(corrupted_rch_filename)
        if os.path.exists(extracted_dir):
            for file in os.listdir(extracted_dir):
                os.remove(os.path.join(extracted_dir, file))
            os.rmdir(extracted_dir)

    def test_non_forceful_extraction_with_bad_crc(self):
        self.logger.info("Testing non-forceful extraction with a bad CRC.")
        corrupted_rch_filename = 'corrupted_archive_no_force.rch'
        extracted_dir = 'extracted_bad_crc_no_force'
        os.makedirs(extracted_dir, exist_ok=True)

        # Step 1: Create a valid RCH archive
        self.rch_handler.pack_rch(self.test_rch_file, [self.test_filename])

        # Step 2: Corrupt the CRC of the file in the archive
        with open(self.test_rch_file, 'rb') as f:
            rch_data = bytearray(f.read())

        # Assuming CRC is stored in the last 4 bytes of each file block for simplicity
        # This might need adjusting based on the actual RCH implementation
        if len(rch_data) > 4:
            rch_data[-4:] = b'\x00\x00\x00\x00'  # Overwriting CRC with zeroes

        # Write the corrupted archive to a new file
        with open(corrupted_rch_filename, 'wb') as f:
            f.write(rch_data)

        # Step 3: Attempt to extract the file without force
        try:
            self.rch_handler.force = False  # Ensure force extraction is disabled
            extracted_file_path = os.path.join(extracted_dir, self.test_filename)
            self.rch_handler.unpack_rch(corrupted_rch_filename, extracted_dir)

            # Check if the file was extracted
            self.assertFalse(os.path.exists(extracted_file_path), "File was extracted despite bad CRC and no force.")
            self.logger.info("Non-forceful extraction with bad CRC correctly did not extract the file.")
        except Exception as e:
            self.fail(f"Non-forceful extraction with bad CRC failed: {str(e)}")
        finally:
            # Cleanup
            if os.path.exists(corrupted_rch_filename):
                os.remove(corrupted_rch_filename)
            if os.path.exists(extracted_dir):
                for file in os.listdir(extracted_dir):
                    os.remove(os.path.join(extracted_dir, file))
                os.rmdir(extracted_dir)


if __name__ == '__main__':
    unittest.main()
