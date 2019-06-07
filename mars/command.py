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

def mars_error(message, returncode=2):
    logger.error(message)
    sys.exit(returncode)

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
        '-o', '--output',
        help="Output file to write config file (default: stdout)")
    parser.add_argument(
        '-c', '--configfile', type=argparse.FileType('r'),
        help="Path to another config file whose values will be added to this one (where possible)")
    parser.add_argument(
        '--force', action='store_true', help="Overwite output file if it exists")
    parser.add_argument(
        "values", nargs=argparse.REMAINDER,
        help=(
            "Config values to be added to the config file in format "
            "`key:value`. Overrides values from other config file if both "
            "present."))
    args = parser.parse_args(argv)
    if args.output and Path(args.output).exists() and not args.force:
        mars_error("Chosen output file exists. Use --force to overwrite.")
    elif args.output:
        output = open(args.output, 'w')
    else:
        output = sys.stdout
            
    old_config = yaml.safe_load(args.configfile) if args.configfile else {}
    # Loading a blank file will return None from yaml.safe_load()
    if old_config is None:
        old_config = {}
    cmdline_kv = {}
    for kv_pair in args.values:
        try:
            key, value = kv_pair.strip().split(":")
            cmdline_kv[key] = value
        except ValueError as e:
            mars_error("Could not parse key:value '{}': {}".format(kv_pair, e))
    update_config(old_config, cmdline_kv)
    config, unused_keys = create_config(**old_config)

    output.write(config)
    
    if unused_keys:
        logger.warn(
            "Warning: the following keys were specified but unused: {}".format(unused_keys))
    logger.info(
        "Config values not specified are commented out in the config file. "
        "Uncomment the relevant lines and add appropriate values as necessary.")

    
def Run(argv):
    usage_str = (
        "%(prog)s <configfile> <workflow> [snakemake options]")
    parser = argparse.ArgumentParser(
        "mars run",
        usage=usage_str,
        description="Executes the MARS pipeline by calling Snakemake.",
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument(
        "configfile",
        help="MARS config file",
        type=argparse.FileType('r'))

    # The remaining args are passed to Snakemake
    args, remaining = parser.parse_known_args(argv)
    
    snakefile = resource_filename("mars", "snakemake/Snakefile")

    logger.info(
        "Validating config file values and paths...")

    config = yaml.safe_load(args.configfile)
    config_schemafile = resource_filename("mars", "data/config.schema.yaml")
    config_schema = yaml.safe_load(open(config_schemafile))

    _missing = check_universal_requirements(config, config_schema)
    if _missing:
        mars_error(
            "The following keys must be defined and uncommented in your config file: {}".format(_missing))
        
    # _missing = check_assembler_requirements(config, config_schema)
    # if _missing:
    #     mars_error(
    #         "Selected assembler ('{}') requires the following keys to be "
    #         "defined and uncommented in your config file: {}".format(config['assembler'], _missing))
    
    config_errors = validate(config, config_schemafile)
    if config_errors:
        logger.warn("Found {} invalid values(s) in config file:".format(len(config_errors)))
        for e in config_errors:
            logger.warn("{}: {}".format(e.key, e.reason))
        mars_error("Invalid values in config file")

    logger.info("Validating sample sheet...")

    samplesheet = config['samplesheet_fp']
    samples = parse_samples(samplesheet)
    samplesheet_errors = validate(samples, resource_filename("mars", "data/samplesheet.schema.yaml"))
    if samplesheet_errors:
        e = samplesheet_errors[0] # There can be only one (from the sample sheet)
        if e.key == "barcode":
            logger.error("  Sheet contains an invalid barcode: ensure all barcodes are numbers between 1-96")
        elif e.key == "sample_label":
            logger.error("  Sheet contains an invalid sample_label: ensure all labels are alphanumeric or ._- characters")
        else:
            logger.error("  Invalid value: {}: {}\n".format(e.key, e.reason))
        mars_error("Invalid rows in sample sheet")
        
    snakemake_args = [
        'snakemake', '--use-conda', '--snakefile', snakefile,
        '--configfile', args.configfile.name, '-p'] + remaining
    dotgraph = subprocess.run(snakemake_args + ["--rulegraph"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    _missing = []
    for target in detect_target_from_dotgraph(dotgraph.stdout.decode(), config_schema):
        _missing += check_target_requirements(target, config, config_schema)
        if _missing:
            mars_error(
                "The selected workflow requires the following keys to be defined "
                "and uncommented in your config file: {}".format(_missing))
    
    logger.info("Executing Snakemake...")

    logger.info("  " + " ".join(snakemake_args))
    cmd = subprocess.run(snakemake_args)
    if cmd.returncode > 0:
        mars_error("Error occurred during Snakemake execution.", cmd.returncode)
    else:
        logger.info("Snakemake finished without errors.")
    return cmd.returncode
        
    
