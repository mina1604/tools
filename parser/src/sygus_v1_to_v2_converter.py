#!/usr/bin/python

import argparse
import sys

from lib.sygus_v1_parser import SygusV1Parser
from lib.symbol_table_builder import SymbolTableBuilder
from lib.sygus_v2_ast_printer import SygusV2ASTPrinter


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file')
    return parser.parse_args()


def _main():
    args = _parse_args()

    with open(args.input_file, 'r') as f:
        contents = f.read()

    parser = SygusV1Parser()
    program = parser.parse(contents)

    if program is None:
        print('Failed to parse.')
        sys.exit(1)

    SymbolTableBuilder.run(program)
    result = SygusV2ASTPrinter.run(program)
    print(result)
    print('\n\n\n')


if __name__ == '__main__':
    _main()
