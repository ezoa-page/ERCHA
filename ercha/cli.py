"""
This software is proprietary and may not be used, copied, modified, or distributed without the express permission of the copyright holder.
"""

import argparse
import sys
import logging
from ercha.logger import logger
from ercha.config import RCH_MAGIC, BLOCK_MAGIC, ENCODING_BZIP2, ENCODING_XOR255, ENCODING_XOR255_LZW
from ercha.rch import RCH

def setup_logging(verbose):
    """Sets up logging configuration based on verbosity."""
    level = logging.DEBUG if verbose else logging.CRITICAL
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')
    logger.debug("Logging initialized.")

def display_results(results):
    """Displays results in a consistent format."""
    logger.info("Displaying results.")
    print(f"{'Filename':<40} {'Size':>10} {'CRC32':>10} {'Encoding':>12} {'CRC Passed':>12} {'Timestamp':>10} {'Status':>20}", file=sys.stderr)
    print("=" * 120, file=sys.stderr)
    for result in results:
        print(f"{result['filename']:<40} {result['size']:>10} {result['crc32']:>10} {result['encoding']:>12} "
              f"{'Yes' if result['crc_passed'] else 'No':>12} {result['timestamp']:>10} {result['status']:>20}", file=sys.stderr)

def handle_pack(args, rch):
    results = rch.pack_rch(args.output, args.input_files, stdin_filename=args.stdin_filename)
    display_results(results)

def handle_unpack(args, rch):
    results = rch.unpack_rch(args.rch_file, args.output_dir, args.files)
    display_results(results)

def handle_check(args, rch):
    results = rch.check_rch(args.rch_file)
    display_results(results)

def handle_inject(args, rch):
    results = rch.inject_files(args.rch_file, args.input_files, stdin_filename=args.stdin_filename)
    display_results(results)

def handle_detract(args, rch):
    removed_files, not_removed_files = rch.detract_files(args.rch_file, args.files_to_remove, args.output)

    if removed_files:
        print(f"Files successfully removed from the archive '{args.output or args.rch_file}': {', '.join(removed_files)}", file=sys.stderr)

    if not_removed_files:
        print(f"Files not found in the archive '{args.output or args.rch_file}' and could not be removed: {', '.join(not_removed_files)}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"All specified files were successfully removed from the archive '{args.output or args.rch_file}'.", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description="Ezoa's Resource Content Handler Archiver")
    subparsers = parser.add_subparsers(dest='command')

    parser.add_argument('--verbose', action='store_true', help='Enable verbose output for logging.')

    # Define subparsers for each command
    pack_parser = subparsers.add_parser('pack', help='Pack files into an RCH archive')
    pack_parser.add_argument('output', help='Output RCH file name or "-" for stdout')
    pack_parser.add_argument('input_files', nargs='*', help='List of input files to pack or "-" for stdin')
    pack_parser.add_argument('--encoding', type=int, default=ENCODING_BZIP2,
                             choices=[ENCODING_BZIP2, ENCODING_XOR255_LZW, ENCODING_XOR255],
                             help='Encoding algorithm (2=BZip2, 0=XOR255+LZW, 1=XOR255)')
    pack_parser.add_argument('--level', type=int, default=9, help='Compression level (1-9)')
    pack_parser.add_argument('--stdin-filename', type=str, default="stdin", help='Filename to use for stdin in the archive')

    unpack_parser = subparsers.add_parser('unpack', help='Unpack files from an RCH archive')
    unpack_parser.add_argument('rch_file', help='RCH file to unpack or "-" for stdin')
    unpack_parser.add_argument('output_dir', help='Directory to extract files to or "-" for stdout')
    unpack_parser.add_argument('--files', nargs='+', help='Specific files to extract')
    unpack_parser.add_argument('--force', action='store_true', help='Force extraction even if CRC check fails')

    check_parser = subparsers.add_parser('check', help='Check the integrity of an RCH archive')
    check_parser.add_argument('rch_file', help='RCH file to check or "-" for stdin')

    inject_parser = subparsers.add_parser('inject', help='Inject additional files into an existing RCH archive')
    inject_parser.add_argument('rch_file', help='Existing RCH file to inject into')
    inject_parser.add_argument('input_files', nargs='+', help='List of input files to inject or "-" for stdin')
    inject_parser.add_argument('--encoding', type=int, default=ENCODING_BZIP2,
                               choices=[ENCODING_BZIP2, ENCODING_XOR255_LZW, ENCODING_XOR255],
                               help='Encoding algorithm (2=BZip2, 0=XOR255+LZW, 1=XOR255)')
    inject_parser.add_argument('--level', type=int, default=9, help='Compression level (1-9)')
    inject_parser.add_argument('--stdin-filename', type=str, default="stdin", help='Filename to use for stdin in the archive')

    detract_parser = subparsers.add_parser('detract', help='Remove one or more files from an RCH archive')
    detract_parser.add_argument('rch_file', help='RCH file from which to remove files')
    detract_parser.add_argument('files_to_remove', nargs='+', help='Names of files to remove from the archive')
    detract_parser.add_argument('--output', help='Output RCH file name (optional, defaults to input file)', default=None)

    args = parser.parse_args()

    setup_logging(args.verbose)
    logger.debug(f"Parsed arguments: {args}")

    rch = RCH(
        encoding_algorithm=getattr(args, 'encoding', ENCODING_BZIP2),
        compression_level=getattr(args, 'level', 9),
        force=getattr(args, 'force', False)
    )

    command_handlers = {
        'pack': handle_pack,
        'unpack': handle_unpack,
        'check': handle_check,
        'inject': handle_inject,
        'detract': handle_detract
    }

    if args.command in command_handlers:
        command_handlers[args.command](args, rch)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == '__main__':
    main()
