import sys
import argparse
import subprocess
import pkg_resources
from . import create_empty_config

def main():

    parser = argparse.ArgumentParser(prog="thrax")
    parser.add_argument("command")

    args, remaining = parser.parse_known_args()

    if args.command == "init":
        Init(remaining)
    elif args.command == "run":
        Run(remaining)

def Init(argv):

    parser = argparse.ArgumentParser(
        "thrax init",
        description = "Creates an empty config file for Thrax")
    parser.add_argument("project_name", help="Name of the project (no spaces)")
    args = parser.parse_args(argv)
    print(create_empty_config(args.project_name))
    

def Run(argv):

    epilog_str = (
        "You can pass any Snakemake arguments to Thrax, e.g:\n"
        "    $ thrax run --cores 12\n"
        " ")

    parser = argparse.ArgumentParser(
        "thrax run",
        usage="%(prog)s [thrax options] [snakemake options]",
        description="Executes the Thrax pipeline by calling Snakemake.",
        epilog=epilog_str,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    # The remaining args passed to Snakemake
    args, remaining = parser.parse_known_args(argv)
    snakefile = pkg_resources.resource_filename("thrax", "data/snakemake/thrax.rules")
        
    snakemake_args = ['snakemake', '--use-conda', '--snakefile', snakefile] + remaining
    print("Running: "+" ".join(snakemake_args))

    cmd = subprocess.run(snakemake_args)
    
    sys.exit(cmd.returncode)
        
    
