import sys
import yaml
import argparse
import tempfile
import subprocess
from pathlib import Path
from pkg_resources import resource_filename

from snakemake.utils import update_config
from snakemake.exceptions import WorkflowError

from . import *
from . import __version__

def mars_error(message):
    sys.stderr.write("MARS: Fatal error: {}\n".format(message))
    sys.exit(2)

def main():
    usage_str = "%(prog)s [--version] <subcommand>"
    description_str = (
        "MARS: MinION Assembly and Reporting System\n\ncommands:\n"
        "  init\tCreate a new config file for a project.\n"
        "  run\tExecute the MARS pipeline.\n")
    parser = argparse.ArgumentParser(
        prog="mars",
        usage=usage_str,
        description=description_str,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False)

    parser.add_argument("command", help=argparse.SUPPRESS, nargs="?")
    parser.add_argument(
        "-v", "--version", action="version",
        version="%(prog)s v{}".format(__version__))

    args, remaining = parser.parse_known_args()

    if args.command == "init":
        Init(remaining)
    elif args.command == "run":
        Run(remaining)
    else:
        parser.print_help()

        
def Init(argv):
    parser = argparse.ArgumentParser(
        "mars init",
        description = "Creates a config file for MARS, optionally populated with values")
    parser.add_argument(
        '-o', '--output', default=sys.stdout, type=argparse.FileType('w'),
        help="Output file to write config file (default: stdout)")
    parser.add_argument(
        "values", nargs=argparse.REMAINDER,
        help="Config values to be added to the config file in format `key:value`")
    args = parser.parse_args(argv)
    values = {}
    for kv_pair in args.values:
        try:
            key, value = kv_pair.strip().split(":")
            values[key] = value
        except ValueError as e:
            mars_error("Could not parse key:value '{}': {}".format(kv_pair, e))

    args.output.write(create_config(**values))
    sys.stderr.write(
        "Note: Config values not specified are commented out in the config file.\n"
        "Uncomment the relevant lines and add appropriate values as necessary.\n")

    
def Run(argv):
    usage_str = (
        "%(prog)s <configfile> [mars options] [snakemake options]")
    epilog_str = (
        "You can pass any Snakemake arguments to MARS, e.g:\n"
        "    $ mars run <configfile> --cores 12\n"
        " ")

    parser = argparse.ArgumentParser(
        "mars run",
        usage=usage_str,
        description="Executes the MARS pipeline by calling Snakemake.",
        epilog=epilog_str,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument(
        "configfile",
        help="MARS config file",
        type=argparse.FileType('r'))

    # The remaining args are passed to Snakemake
    args, remaining = parser.parse_known_args(argv)
    
    snakefile = resource_filename("mars", "snakemake/Snakefile")

    sys.stderr.write(
        "MARS: Validating config file values and paths...\n")

    config = yaml.load(args.configfile)
    config_schemafile = resource_filename("mars", "data/config.schema.yaml")
    config_schema = yaml.load(open(config_schemafile))

    _missing = check_universal_requirements(config, config_schema)
    if _missing:
        mars_error(
            "The following keys must be defined and uncommented in your config file: {}".format(_missing))
        
    # _missing = check_target_requirements(target, config, config_schema)
    # if _missing:
    #     mars_error(
    #         "Selected workflow ('{}') requires the following keys to be "
    #         "defined and uncommented in your config file: {}".format(target, _missing))

    _missing = check_assembler_requirements(config, config_schema)
    if _missing:
        mars_error(
            "Selected assembler ('{}') requires the following keys to be "
            "defined and uncommented in your config file: {}".format(config['assembler'], _missing))
    
    config_errors = validate(config, config_schemafile)
    if config_errors:
        sys.stderr.write("  Found {} invalid values(s) in config file:\n".format(len(config_errors)))
        for e in config_errors:
            sys.stderr.write("  - {}: {}\n".format(e.key, e.reason))
        mars_error("Invalid values in config file")

    sys.stderr.write("MARS: Validating sample sheet...\n")

    samplesheet = config['samplesheet_fp']
    samples = parse_samples(samplesheet)
    samplesheet_errors = validate(samples, resource_filename("mars", "data/samplesheet.schema.yaml"))
    if samplesheet_errors:
        e = samplesheet_errors[0] # There's only ever one
        if e.key == "barcode":
            sys.stderr.write("  Sheet contains an invalid barcode: ensure all barcodes are numbers between 1-96\n")
        elif e.key == "sample_label":
            sys.stderr.write("  Sheet contains an invalid sample_label: ensure all labels are alphanumeric or ._- characters\n")
        else:
            sys.stderr.write("  Invalid value: {}: {}\n".format(e.key, e.reason))
        mars_error("Invalid rows in sample sheet")
        
    sys.stderr.write("MARS: Resolving paths in config file...\n")
    config = resolve_paths(config)

    tmp_config_fp = ''
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_config:
        yaml.dump(config, tmp_config)
        tmp_config_fp = tmp_config.name
    sys.stderr.write("MARS: Updated config file written to '{}'\n".format(tmp_config_fp))

    snakemake_args = [
        'snakemake', '--use-conda', '--snakefile', snakefile,
        '--configfile', tmp_config_fp] + remaining
    dotgraph = subprocess.run(snakemake_args + ["--rulegraph"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    _missing = []
    for target in detect_target_from_dotgraph(dotgraph.stdout.decode(), config_schema):
        print(target)
        _missing += check_target_requirements(target, config, config_schema)
        if _missing:
            mars_error(
                "The selected workflow requires the following keys to be defined "
                "and uncommented in your config file: {}".format(_missing))
    
    sys.stderr.write("MARS: Executing Snakemake:\n")

    snakemake_args = [
        'snakemake', '--use-conda', '--snakefile', snakefile,
        '--configfile', tmp_config_fp] + remaining
    sys.stderr.write("  {}\n\n".format(" ".join(snakemake_args)))
    cmd = subprocess.run(snakemake_args)
    if cmd.returncode > 0:
        sys.stderr.write("MARS: Error occurred during Snakemake execution.\n")
    else:
        sys.stderr.write("MARS: Exiting without errors.\n")
    return cmd.returncode
        
    
