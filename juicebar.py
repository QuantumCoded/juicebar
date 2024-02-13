from mako.template import Template
from packaging import version

import argparse
import os
import questionary
import re
import requests
import sys

def get_args():
    class MyArgParser(argparse.ArgumentParser):
        def error(self, message):
            sys.stderr.write('error: %s\n' % message)
            self.print_help()
            sys.exit(2)

    parser = MyArgParser(description="Juice Bar")
    parser.add_argument(
        "--nixos-dir",
		nargs="?",
		const="default",
        help="Change the /etc/nixos path",
    )
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

def ask_many_strings(question, func=None,):
    strings = []
    while True:
        string_input = questionary.text(
            question + " (Leave blank to finish):"
        ).ask()

        if not string_input:
            break

        if func:
            func(string_input)

        strings.append(string_input)

    return strings

def juice_bar(nixos_dir):
    if not nixos_dir:
        nixos_dir = "/etc/nixos"

    mkdirs = [
        nixos_dir + "/home",
        nixos_dir + "/hosts",
        nixos_dir + "/modules",
        nixos_dir + "/modules/nixos",
    ]

    for path in mkdirs:
        if not os.path.exists(path):
            os.mkdir(path)

    unstable = False
    choices = ["Unstable (rolling)", "Other"]
    latest_release = get_latest_release()
    latest_release_choice = "Latest ({release})".format(release=latest_release) 

    if latest_release:
        choices.insert(0, latest_release_choice)

    release = questionary.select(
        "What NixOS release would you like to use?",
        choices=choices,
    ).ask()

    match release:
        case "Unstable (rolling)":
            release = "unstable"
            unstable = True
        case "Other":
            release = questionary.text(
                "What NixOS release would you like to use? (Accepts version or branch):"
            ).ask()
        case _:
            release = latest_release

    if not "-" in release:
        release = "nixos-" + release

    home_manager = questionary.confirm(
        "Would you like to use home-manager? (Home config without this is impure)"
    ).ask()

    host_strings = ask_many_strings("Enter machines in username@hostname pairs.")
    host_pairs = []
    users = []
    hosts = []

    for string in host_strings:
        user, host = string.split("@") 
        host_pairs.append((user, host))
        users.append(user)
        hosts.append(host)
    
    arches = {}
    arch_choices = [
      "aarch64-darwin",
      "aarch64-linux",
      "x86_64-darwin",
      "x86_64-linux",
      "Other",
    ]

    for host in hosts:
        question = "What arch does host '" + host + "' use?"
        arch = questionary.select(
            question,
            choices=arch_choices
        ).ask()

        if arch == "Other":
            arch = questionary.text(question).ask()

        arches[host] = arch

    use_roles = questionary.confirm(
        "Would you like to use a role based configuration for these machines?",
        default=False,
    ).ask()

    roles = {}
    if use_roles:
        for host in hosts:
            roles[host] = ask_many_strings(
                "Roles to use for machine '{host}'?".format(host=host)
            )

    for user, host in host_pairs:
        user_path = nixos_dir + "/home/" + user
        home_path = user_path + "/" + host + ".nix"
        hostdir_path = nixos_dir + "/hosts/" + host
        host_path = hostdir_path + "/default.nix"

        if not os.path.exists(user_path):
            os.mkdir(user_path)

        if not os.path.exists(hostdir_path):
            os.mkdir(hostdir_path)
        
        if not os.path.exists(home_path):
            template = Template(filename="templates/home")
            file = open(home_path, "w")
            file.write(template.render(
                release=release,
                user=user,
            ))
            file.close()
        else:
            print("warning: '" + home_path + "' exists, not overwriting")

        if not os.path.exists(host_path):
            template = Template(filename="templates/host")
            file = open(host_path, "w")
            file.write(template.render(
                use_roles=use_roles,
                roles=roles[host].sort(),
            ))
            file.close()
        else:
            print("warning: '" + host_path + "' exists, not overwriting")

    shared_config = questionary.confirm(
        "Would you like to make a common config for all machines?",
        default=False,
    ).ask()

    if shared_config:
        path = nixos_dir + "/common.nix"
        if not os.path.exists(path):
            file = open(path, "w")
            file.write("{}")
            file.close()
        else:
            print("warning: '" + path + "' exists, not overwriting")

    toplevel = question.text(
        "What would you like to call your top level attribute?"
    ).ask()

    nixos_modules = ask_many_strings(
        "Any NixOS modules to create?",
        func=lambda string: juice_module("nixos", string, toplevel),
    )

    if home_manager:
        path = nixos_dir + "/modules/home-manager"
        module_path = nixos_dir + "/modules/nixos/home-manager.nix"

        if not os.path.exists(path):
            os.mkdir(path)

        if not os.path.exists(module_path):
            template = Template(filename="templates/home-manager")
            file = open(module_path, "w")
            file.write(template.render(
                toplevel=toplevel,
                users=users.sort(),
            ))
            file.close()
        else:
            print("warning: '" + module_path + "' exists, not overwriting")

        home_manager_modules = ask_many_strings(
            "Any home-manager modules to create?",
            func=lambda string: juice_module("home-manager", string, toplevel),
        )
    
    allow_unfree = questionary.confirm(
        "Would you like to allow unfree packages in flake.nix?"
    ).ask()

    flake_path = nixos_dir + "/flake.nix"
    if not os.path.exists(flake_path):
        template = Template(filename="templates/flake")
        file = open(flake_path, "w")
        file.write(template.render(
            unstable=unstable,
            home_manager=home_manager,
            allow_unfree=allow_unfree,
            shared_config=shared_config,
            hosts=hosts.sort(),
            host_strings=host_strings.sort(),
            arches=arches
        ))
        file.close()
    else:
        print("warning: '" + flake_path + "' exists, not overwriting")

    if not use_roles:
        move_configs = questionary.confirm(
            "Do you have an existing configuration.nix and " +
            "hardware-configuration.nix you would like to move into place?"
        )

        if move_configs:
            host = questionary.text(
                "What is the hostname of this system?"
            )

            os.rename(
                nixos_dir + "/configuration.nix",
                nixos_dir + "/hosts/{host}/configuration.nix".format(host=host),
            )

            os.rename(
                nixos_dir + "/hardware-configuration.nix",
                nixos_dir + "/hosts/{host}/hardware.nix".format(host=host),
            )

def juice_module(system=None, name=None, toplevel=None):
    if not system:
        system = questionary.text(
            "What module system should this module be made for?"
        ).ask()

    if not name:
        name = questionary.text(
            "What is the name of this {system} module?".format(system=system)
        ).ask()

    if not toplevel:
        toplevel = questionary.text(
            "What is your top level attribute?"
        ).ask()

    module_path = nixos_dir + "/" + system + "/" + name + ".nix"
    if not os.path.exists(module_path):
        template = Template(filename="templates/module")
        file = open(module_path, "w")
        file.write(template.render(
            toplevel=toplevel
        ))
    else:
        print("warning: '" + module_path + "' exists, not overwriting")
    
args = get_args()

if args.command in ["bar", "b"]:
    juice_bar(args.nixos_dir)

if args.command in ["module", "mod", "m"]:
    print("TODO!")
    # juice_module()
