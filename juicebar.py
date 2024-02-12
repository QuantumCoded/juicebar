from mako.template import Template
from packaging import version

import argparse
import re
import questionary
import requests
import sys

def get_args():
    class MyArgParser(argparse.ArgumentParser):
        def error(self, message):
            sys.stderr.write('error: %s\n' % message)
            self.print_help()
            sys.exit(2)

    parser = MyArgParser(description="Juice Bar")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "bar",
        aliases=["bar", "b"],
        help="Create NixOS repo from scratch",
    )
    subparsers.add_parser(
        "module",
        aliases=["module", "mod", "m"],
        help="Create Nix module from scratch",
    )

    return parser.parse_args()

def get_nixpkgs_branches():
    api_url = "https://api.github.com/repos/NixOS/nixpkgs/branches?per_page=100"
    nixpkgs_branches = []

    page = 1
    while True:
        response = requests.get(api_url + "&page={page}".format(page=page))

        if response.status_code == 200:
            json = response.json()

            branches = [branch["name"] for branch in json]

            if not branches:
                break
            
            nixpkgs_branches.extend(branches)
            page += 1
        else:
            print("Failed to fetch nixpkgs branches")
            return None

    return nixpkgs_branches

def get_latest_release():
    latest_release = None

    release_regex = re.compile(r"release-(\d+\.\d+)")

    for branch in get_nixpkgs_branches():
        release_match = release_regex.match(branch)
        if release_match:
            release = release_match.group(1)
            if (
                latest_release is None
                or version.parse(release) > version.parse(latest_release)
            ):
                latest_release = release

    return latest_release

def juice_bar():
    print("juice!")
    return

args = get_args()

if args.command in ["bar", "b"]:
    juice_bar()

if args.command in ["module", "mod", "m"]:
    print("TODO!")

