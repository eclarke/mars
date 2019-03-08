import sys
import yaml
import argparse
import tempfile
import subprocess
from pathlib import Path
from pkg_resources import resource_filename

from snakemake.utils import validate, update_config
from snakemake.exceptions import WorkflowError

from . import *
from . import __version__

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
        usage="%(prog)s [-o output_dir] [-s samplesheet_fp] > config.yaml",
        description = "Creates an empty config file for MARS",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        '-o', '--output_dir', required=True,
        help="Desired MARS output directory for this project")
    parser.add_argument(
        '-s', '--samplesheet_fp', required=True,
        help="Path to sample sheet for this project")

    args = parser.parse_args(argv)
    output_dir = str(Path(args.output_dir).expanduser().resolve())
    samplesheet_fp = str(Path(args.samplesheet_fp).expanduser().resolve())
    sys.stdout.write(create_empty_config(output_dir, samplesheet_fp))
    sys.stderr.write(
        "Note: Optional options are commented out in the config file.\n"
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

    sys.stderr.write("MARS: Loading config file and sample sheet...\n")
    config = yaml.load(args.configfile)
    samplesheet = config.get('samplesheet_fp')
    if samplesheet is None:
        raise ValueError(
            "No valid sample sheet path found in config file.\nSpecify one using"
            " in the config file under 'samplesheet_fp'.")
    if not Path(samplesheet).exists() or not Path(samplesheet).is_file():
        raise ConfigPathError(
            "Path to specified sample sheet in config file is not a "
            "file or does not exist.")

    # All metadata values are added to the config file as key:value pairs
    # for validation
    sys.stderr.write("MARS: Reading metadata header from sample sheet...\n")
    try:
        metadata = parse_metadata(samplesheet)
        sys.stderr.write(
            "MARS: Found {} metadata keys(s) in sample sheet: {}\n".format(
                len(metadata), list(metadata.keys())))
        if metadata:
            sys.stderr.write("  Updating config file with metadata keys...\n")
            update_config(config, metadata)
    except ValueError as e:
        raise e
        sys.stderr.write(
            "  Non-fatal error parsing metadata in sample sheet: \n\t{}: {}\n"
            "  Ensure the metadata lines follow the format '# key[tab]value'.\n"
            "  Ignoring metadata and continuing...\n".format(type(e).__name__, e))

    sys.stderr.write(
        "MARS: Validating config file values and paths...\n")

    config_schema = resource_filename("mars", "data/config.schema.yaml")
    validate(config, config_schema)
    validate_paths(config, config_schema)

    sys.stderr.write("MARS: Validating sample sheet...\n")
    samples = parse_samples(samplesheet)
    validate(samples, resource_filename("mars", "data/samplesheet.schema.yaml"))

    sys.stderr.write("MARS: Resolving paths in config file...\n")
    config = resolve_paths(config)
    tmp_config_fp = ''
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_config:
        yaml.dump(config, tmp_config)
        tmp_config_fp = tmp_config.name
    sys.stderr.write("MARS: Updated config file saved to '{}'\n".format(tmp_config_fp))
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
        
    
