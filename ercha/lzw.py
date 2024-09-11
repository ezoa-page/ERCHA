"""
This software is proprietary and may not be used, copied, modified, or distributed without the express permission of the copyright holder.
"""

"""
Had to implement our own LZW handler because there is no stable LZW dependencies we can utitlize in Python as of writing this.
"""

from ercha.logger import logger  # Relative import

class LZWBase:
    """Base class for shared LZW functionalities."""

    def __init__(self):
        self.reset_dictionary()
        logger.debug(f"Initialized {self.__class__.__name__}.")

    def reset_dictionary(self):
        """Reset the dictionary to its initial state."""
        self.dictionary = {bytes([i]): i for i in range(256)}
        self.reverse_dictionary = {i: bytes([i]) for i in range(256)}
        self.next_code = 256

    def can_add_to_dictionary(self):
        """Check if a new entry can be added to the dictionary."""
        return self.next_code < 65536

    def add_to_dictionary(self, key, value):
        """Add a new entry to the dictionary."""
        if self.can_add_to_dictionary():
            self.dictionary[key] = self.next_code
            self.reverse_dictionary[self.next_code] = value
            self.next_code += 1


class LZWCompressor(LZWBase):
    """Class to handle LZW encoding."""

    def encode(self, data):
        """Encode data using LZW algorithm."""
        logger.debug(f"Starting encoding for data of size {len(data)} bytes.")
        string = b""
        encoded_data = []

        for symbol in data:
            string_plus_symbol = string + bytes([symbol])
            if string_plus_symbol in self.dictionary:
                string = string_plus_symbol
            else:
                encoded_data.append(self.dictionary[string])
                self.add_to_dictionary(string_plus_symbol, string_plus_symbol)
                string = bytes([symbol])

        if string:
            encoded_data.append(self.dictionary[string])

        result = self._to_bytes(encoded_data)
        logger.debug(f"Compression completed. Encoded size is {len(result)} bytes.")
        return result

    def _to_bytes(self, encoded_data):
        """Convert encoded data to bytes."""
        compressed_bytes = bytearray()
        for code in encoded_data:
            compressed_bytes.extend(code.to_bytes(2, byteorder='big'))
        return compressed_bytes



class LZWDecompressor(LZWBase):
    """Class to handle LZW decoding."""

    def decode(self, encoded_data):
        """Decode data using LZW algorithm."""
        logger.debug(f"Starting decoding for data of size {len(encoded_data)} bytes.")
        decoded_data = bytearray()
        codes = self._from_bytes(encoded_data)

        if not codes:
            logger.error("LZW decoding failed: no data to decode.")
            raise ValueError("LZW decoding failed: no data to decode.")

        string = self.reverse_dictionary[codes.pop(0)]
        decoded_data.extend(string)

        for code in codes:
            entry = self._get_entry(code, string)
            decoded_data.extend(entry)
            self.add_to_dictionary(string + entry[0:1], string + entry[0:1])
            string = entry

        result = bytes(decoded_data)
        logger.debug(f"Decompression completed. Decoded size is {len(result)} bytes.")
        return result

    def _from_bytes(self, encoded_data):
        """Convert bytes to list of codes."""
        return [
            int.from_bytes(encoded_data[i:i + 2], byteorder='big')
            for i in range(0, len(encoded_data), 2)
        ]

    def _get_entry(self, code, string):
        """Get the dictionary entry for a given code."""
        if code in self.reverse_dictionary:
            return self.reverse_dictionary[code]
        elif code == self.next_code:
            return string + string[0:1]
        else:
            logger.error("Invalid LZW code encountered.")
            raise ValueError("Invalid LZW code encountered.")
