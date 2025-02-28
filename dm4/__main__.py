"""
Created on Sep 12, 2013

@author: u0490822
"""
import sys
from dm4.dm4file import DM4File
from dm4.helpers import print_tag_directory_tree, print_tag_data


def main():
    if len(sys.argv) < 2 or len(sys.argv) > 2:
        print("Usage: python -m dm4 <dm4_input_fullpath>")
        print()
        print("Invoking dm4 as a module prints the tag directory tree of a Digital Micrograph 4 (DM4) file.")
        sys.exit(1)

    dm4_input_fullpath = sys.argv[1]

    with DM4File.open(dm4_input_fullpath) as dm4file:
        tags = dm4file.read_directory()
        print_tag_directory_tree(dm4file, tags)


if __name__ == '__main__':
    main()
