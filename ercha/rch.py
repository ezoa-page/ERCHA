"""
This software is proprietary and may not be used, copied, modified, or distributed without the express permission of the copyright holder.
"""

"""
RCH file handler.
"""

import os
import sys
import zlib
import bz2
import struct
from ercha.logger import logger  # Relative import
from ercha.config import RCH_MAGIC, BLOCK_MAGIC, ENCODING_BZIP2, ENCODING_XOR255, ENCODING_XOR255_LZW  # Relative import
from ercha.lzw import LZWCompressor, LZWDecompressor  # Relative import


class RCH:
    """Class to handle RCH file operations."""

    def __init__(self, encoding_algorithm=ENCODING_BZIP2, compression_level=9, force=False):
        self.encoding_algorithm = encoding_algorithm
        self.compression_level = compression_level
        self.force = force
        logger.info(f"Initialized RCH with encoding_algorithm={encoding_algorithm}, compression_level={compression_level}, force={force}")

    def xor255(self, data):
        """Apply XOR255 operation to the data."""
        """XOR is hypothesized to have been used to ensure CRC checks don't give false positives due to the amount of repeated bytes"""
        logger.debug("Applying XOR255 operation.")
        return bytes([b ^ 255 for b in data])

    def read_rch_header(self, rch_file):
        """Reads and validates the RCH file header."""
        logger.info("Reading RCH header.")
        header = rch_file.read(4)
        if header != RCH_MAGIC:
            logger.error(f"Invalid RCH file format: expected {RCH_MAGIC}, got {header}")
            raise ValueError("Invalid RCH file format")
        rch_file.read(4 + 4 + 16)  # Skip container version, creation timestamp, and reserved
        logger.debug("RCH header read successfully.")

    def read_file_block_header(self, rch_file):
        """Reads the header of a file block."""
        logger.info("Reading file block header.")
        block_magic = rch_file.read(2)
        if block_magic != BLOCK_MAGIC:
            logger.error(f"Invalid block magic number: expected {BLOCK_MAGIC}, got {block_magic}")
            raise ValueError("Invalid block magic number")

        filename = rch_file.read(40).split(b'\x00', 1)[0].decode('utf-8')
        header = struct.unpack('<I I I I I', rch_file.read(4 * 5))
        logger.info(f"File block header read for {filename}.")
        return filename, header[2], header[3], header[4], header[1]

    def decode_data(self, file_data, encoding_algo):
        """Decompresses the file data using the specified encoding algorithm."""
        logger.info(f"Decompressing data using algorithm {encoding_algo}.")
        try:
            if encoding_algo == ENCODING_BZIP2:
                result = bz2.decompress(file_data)
            elif encoding_algo == ENCODING_XOR255_LZW:
                lzw_data = LZWDecompressor().decode(file_data)
                result = self.xor255(lzw_data)
            elif encoding_algo == ENCODING_XOR255:
                result = self.xor255(file_data)
            else:
                logger.error("Unknown encoding algorithm.")
                raise ValueError("Unknown encoding algorithm")
            logger.debug(f"Decompression successful. Output size is {len(result)} bytes.")
            return result
        except ValueError as ve:
            logger.error(f"Decompression failed: {ve}")
            raise  # Re-raise without nesting
        except OSError as oe:
            logger.error(f"Decompression failed: BZIP2 decoding failed: {oe}")
            raise ValueError(f"Decompression failed: BZIP2 decoding failed: {oe}")
        except Exception as e:
            logger.error(f"Decompression failed: {e}")
            raise ValueError(f"Decompression failed: {e}")

    def check_crc(self, data, crc32_stored):
        """Checks the CRC32 value of the data."""
        crc32_computed = zlib.crc32(data) & 0xFFFFFFFF
        result = crc32_computed == crc32_stored
        logger.debug(f"CRC check: computed={crc32_computed}, stored={crc32_stored}, result={result}")
        if not result:
            logger.error("CRC check failed")
            raise ValueError("CRC check failed")
        return result

    def write_block_to_file(self, rch_file, filename, encoded_data, crc32):
        """Writes a file block to the RCH archive."""
        logger.info(f"Writing block to file for {filename.decode('utf-8')}.")
        rch_file.write(BLOCK_MAGIC)
        rch_file.write(filename.ljust(40, b'\x00'))
        rch_file.write(struct.pack('<I I I I I',
                                   1, 0, len(encoded_data), crc32, self.encoding_algorithm))
        rch_file.write(encoded_data)
        logger.debug(f"Block written to file for {filename.decode('utf-8')}.")

    def pack_rch(self, output_filename, input_files, append=False, stdin_filename="stdin"):
        """Packs multiple files into a single RCH archive with specified encoding."""
        mode = 'ab' if append else 'wb'
        results = []
        logger.info(f"Packing files into RCH archive: {output_filename}")
        with (sys.stdout.buffer if output_filename == '-' else open(output_filename, mode)) as rch_file:
            if not append:
                self._write_rch_header(rch_file)

            for input_file in input_files:
                file_data = self.read_input_file(input_file)
                filename = stdin_filename.encode('utf-8') if input_file == '-' else os.path.basename(input_file).encode('utf-8')
                result = self._write_file_block(rch_file, filename, file_data)
                results.append(result)
                logger.info(f"Packed {filename.decode('utf-8')} into RCH archive.")

        logger.info(f"Packing completed for {output_filename}.")
        return results

    def _write_rch_header(self, rch_file):
        """Writes the RCH file header."""
        logger.info("Writing RCH header.")
        rch_file.write(RCH_MAGIC)
        rch_file.write(struct.pack('<I', 1))  # Container version
        rch_file.write(struct.pack('<I', 0))  # Creation timestamp (unused)
        rch_file.write(b'\x00' * 16)          # Reserved
        logger.debug("RCH header written successfully.")

    def _write_file_block(self, rch_file, filename, file_data):
        """Writes a file block with encoded data."""
        logger.info(f"Writing file block for {filename.decode('utf-8')}.")
        encoded_data = self.encode_file_data(file_data)
        crc32 = self._calculate_crc32(file_data, encoded_data)
        self.write_block_to_file(rch_file, filename, encoded_data, crc32)

        return {
            'filename': filename.decode('utf-8').strip(),
            'size': len(encoded_data),
            'crc32': crc32,
            'encoding': self.get_encoding_name(self.encoding_algorithm),
            'crc_passed': True,
            'timestamp': 0,
            'status': 'Packed'
        }

    def _calculate_crc32(self, file_data, encoded_data):
        """Calculates CRC32 for the given data."""
        crc = (zlib.crc32(file_data) & 0xFFFFFFFF
               if self.encoding_algorithm == ENCODING_BZIP2
               else zlib.crc32(encoded_data) & 0xFFFFFFFF)
        logger.debug(f"CRC32 calculated: {crc}")
        return crc

    def read_input_file(self, input_file):
        """Reads data from a file or stdin."""
        logger.info(f"Reading input file: {input_file}")
        try:
            if input_file == '-':
                data = sys.stdin.buffer.read()
            else:
                with open(input_file, 'rb') as f:
                    data = f.read()
            logger.debug(f"Read {len(data)} bytes from {input_file}")
            return data
        except Exception as e:
            logger.exception(f"Failed to read input file {input_file}: {e}")
            raise

    def encode_file_data(self, file_data):
        """Compresses the file data based on the specified encoding algorithm."""
        logger.info(f"Compressing file data with algorithm {self.encoding_algorithm}.")
        try:
            if self.encoding_algorithm == ENCODING_BZIP2:
                encoder = bz2.BZ2Compressor(self.compression_level)
                result = encoder.compress(file_data) + encoder.flush()
            elif self.encoding_algorithm == ENCODING_XOR255_LZW:
                xor_data = self.xor255(file_data)
                result = LZWCompressor().encode(xor_data)
            elif self.encoding_algorithm == ENCODING_XOR255:
                result = self.xor255(file_data)
            else:
                logger.error("Unknown encoding algorithm.")
                raise ValueError("Unknown encoding algorithm")
            logger.debug(f"Compression successful. Encoded size is {len(result)} bytes.")
            return result
        except Exception as e:
            logger.exception(f"Compression failed: {e}")
            raise

    def unpack_rch(self, rch_filename, output_directory, filenames=None):
        """Unpacks an RCH archive into the specified directory."""
        logger.info(f"Unpacking RCH archive: {rch_filename}")
        results = []
        with (sys.stdin.buffer if rch_filename == '-' else open(rch_filename, 'rb')) as rch_file:
            self.read_rch_header(rch_file)

            while True:
                try:
                    filename, filesize, crc32_stored, encoding_algo, timestamp = self.read_file_block_header(rch_file)
                    safe_filename = self._sanitize_filename(filename)  # Initialize here

                    file_data = rch_file.read(filesize)
                    logger.debug(f"Read {len(file_data)} bytes for {filename}. Safe filename: {safe_filename}")

                    if not filenames or filename in filenames:
                        try:
                            output_data, crc_valid = self._process_file_data(file_data, encoding_algo, crc32_stored)

                            # Modified part to handle force flag
                            if not crc_valid and not self.force:
                                logger.warning(f"CRC check failed for {safe_filename}")
                                raise ValueError("CRC check failed.")

                            self._write_output(output_directory, safe_filename, output_data)
                            result_status = 'Unpacked' if crc_valid or self.force else 'Failed'
                            results.append(self._create_result_entry(safe_filename, filesize, crc32_stored, encoding_algo, crc_valid, timestamp, result_status))
                            logger.info(f"File {safe_filename} unpacked with status: {result_status}")
                        except ValueError as e:
                            logger.error(f"Error unpacking file {safe_filename}: {e}")
                            results.append(self._create_result_entry(safe_filename, filesize, crc32_stored, encoding_algo, False, timestamp, 'Failed'))
                            continue  # Skip to next file

                except ValueError:
                    logger.info("No more blocks to read; exiting.")
                    break

        logger.info(f"Unpacking completed for {rch_filename}. Results: {results}")
        return results


    def _process_file_data(self, file_data, encoding_algo, crc32_stored):
        """Processes the file data by decompressing and checking CRC."""
        logger.debug(f"Processing file data with encoding algorithm {encoding_algo}.")
        output_data = self.decode_data(file_data, encoding_algo)
        crc_valid = self.check_crc(output_data if encoding_algo == ENCODING_BZIP2 else file_data, crc32_stored)
        logger.debug(f"CRC check result: {crc_valid}")
        return output_data, crc_valid

    def _sanitize_filename(self, filename):
        """Sanitizes the filename to prevent path traversal and ensures it is not too long."""
        logger.debug(f"Sanitizing filename: {filename}")
        sanitized = os.path.basename(filename)
        if sanitized != filename:
            logger.warning(f"Path traversal detected. Using sanitized filename: {sanitized}")
        if len(sanitized) > 255:
            root, ext = os.path.splitext(sanitized)
            sanitized = root[:255 - len(ext)] + ext
            logger.debug(f"Truncated filename to avoid excessive length: {sanitized}")
        return sanitized

    def _write_output(self, output_directory, filename, output_data):
        """Writes the decoded data to the output directory or stdout."""
        logger.info(f"Writing output to {filename}")
        try:
            if output_directory == '-':
                sys.stdout.buffer.write(output_data)
            else:
                output_path = os.path.join(output_directory, filename)
                os.makedirs(output_directory, exist_ok=True)
                with open(output_path, 'wb') as out_file:
                    out_file.write(output_data)
                logger.debug(f"Wrote {len(output_data)} bytes to {output_path}")
        except Exception as e:
            logger.exception(f"Failed to write output to {filename}: {e}")
            raise

    def _create_result_entry(self, filename, filesize, crc32_stored, encoding_algo, crc_valid, timestamp, status):
        """Creates a result entry for display."""
        logger.debug(f"Creating result entry for {filename}.")
        return {
            'filename': filename,
            'size': filesize,
            'crc32': crc32_stored,
            'encoding': self.get_encoding_name(encoding_algo),
            'crc_passed': crc_valid,
            'timestamp': timestamp,
            'status': status
        }

    def check_rch(self, rch_filename):
        """Checks the integrity of an RCH archive and lists file details with CRC status."""
        logger.info(f"Checking RCH archive: {rch_filename}")
        results = []
        with (sys.stdin.buffer if rch_filename == '-' else open(rch_filename, 'rb')) as rch_file:
            self.read_rch_header(rch_file)

            while True:
                try:
                    filename, filesize, crc32_stored, encoding_algo, timestamp = self.read_file_block_header(rch_file)
                except ValueError:
                    logger.info("No more blocks to read; exiting.")
                    break

                file_data = rch_file.read(filesize)
                logger.debug(f"Read {len(file_data)} bytes for {filename}.")

                try:
                    crc_valid = self._verify_crc(file_data, encoding_algo, crc32_stored)
                    logger.info(f"CRC check for {filename}: {crc_valid}")
                except ValueError as e:
                    crc_valid = False  # If decoding fails, CRC check fails
                    logger.error(f"Error checking CRC for file {filename}: {e}")

                safe_filename = self._sanitize_filename(filename)
                results.append(self._create_result_entry(safe_filename, filesize, crc32_stored, encoding_algo, crc_valid, timestamp, 'Checked'))

        logger.info(f"Checking completed for {rch_filename}.")
        return results

    def _verify_crc(self, file_data, encoding_algo, crc32_stored):
        """Verifies CRC based on the encoding algorithm."""
        logger.debug(f"Verifying CRC for data with encoding algorithm {encoding_algo}.")
        if encoding_algo == ENCODING_BZIP2:
            deencoded_data = self.decode_data(file_data, encoding_algo)
            return self.check_crc(deencoded_data, crc32_stored)
        else:
            return self.check_crc(file_data, crc32_stored)

    def get_encoding_name(self, encoding_algo):
        """Returns the name of the encoding algorithm."""
        name = {
            ENCODING_BZIP2: 'BZIP2',
            ENCODING_XOR255_LZW: 'XOR255+LZW',
            ENCODING_XOR255: 'XOR255'
        }.get(encoding_algo, 'Unknown')
        logger.debug(f"Encoding algorithm {encoding_algo} name is {name}.")
        return name

    def inject_files(self, rch_filename, input_files, stdin_filename="stdin"):
        """Injects additional files into an existing RCH archive."""
        logger.info(f"Injecting files into {rch_filename}")
        return self.pack_rch(rch_filename, input_files, append=True, stdin_filename=stdin_filename)

    def detract_file(self, rch_filename, file_to_remove, output_filename=None):
        """Removes a specific file from the RCH archive."""
        output_filename = output_filename or rch_filename
        temp_filename = output_filename + ".tmp"
        file_removed = False

        logger.info(f"Detracting file {file_to_remove} from {rch_filename}")

        with open(rch_filename, 'rb') as rch_file, open(temp_filename, 'wb') as temp_file:
            temp_file.write(rch_file.read(4 + 4 + 4 + 16))  # Copy RCH header

            while True:
                try:
                    current_pos = rch_file.tell()
                    filename, filesize, crc32_stored, encoding_algo, timestamp = self.read_file_block_header(rch_file)
                except ValueError:
                    logger.info("No more blocks to read; exiting.")
                    break

                file_data = rch_file.read(filesize)

                if filename != file_to_remove:
                    rch_file.seek(current_pos)
                    temp_file.write(rch_file.read(2 + 40 + 4 * 5 + filesize))
                else:
                    file_removed = True
                    logger.debug(f"File {file_to_remove} found and removed.")

        if file_removed:
            os.rename(temp_filename, output_filename)
            logger.info(f"File {file_to_remove} removed from the archive.")
        else:
            os.remove(temp_filename)
            logger.warning(f"File {file_to_remove} not found in the archive.")

        return file_removed

    def detract_files(self, rch_filename, files_to_remove, output_filename=None):
        """Removes multiple files from the RCH archive."""
        # If output_filename is provided, copy the original RCH file to output_filename
        if output_filename:
            with open(rch_filename, 'rb') as src, open(output_filename, 'wb') as dst:
                dst.write(src.read())
            rch_filename = output_filename

        removed_files = []
        not_removed_files = []

        for file_to_remove in files_to_remove:
            file_removed = self.detract_file(rch_filename, file_to_remove)
            if file_removed:
                removed_files.append(file_to_remove)
            else:
                not_removed_files.append(file_to_remove)

        return removed_files, not_removed_files

