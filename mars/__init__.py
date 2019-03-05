import sys
import yaml
import warnings
from pathlib import Path
from itertools import chain
from pkg_resources import resource_stream, get_distribution

import pandas as pd

__version__ = get_distribution(__name__).version

def padded_barcodes(samples):
    return [str(b).zfill(2) for b in samples.barcode]

def parse_metadata(samplesheet_fp):
    metadata = {}
    with open(samplesheet_fp) as samplesheet:
        for line in samplesheet:
            if line.startswith("#"):
                key, value = line.strip("# ").split('\t')
                metadata[key] = value.strip()
    return metadata

def parse_samples(samplesheet_fp):
    return pd.read_csv(
        samplesheet_fp,
        header=0,
        comment="#",
        dtype={'sample_id':'str', 'sample_label':'str', 'description':'str'},
        sep='\t')

class ConfigPathWarning(UserWarning):
    pass

class ConfigPathError(ValueError):
    pass

def validate_paths(config, schema):
    schema = yaml.load(open(schema).read())
    updated_config = config

    # By default the warnings show source file and source line.
    # This makes warnings just show the warning category and message.
    def formatwarning(message, category, filename, lineno, line):
        return "  {}: {}\n".format(category.__name__, message)
    warnings.formatwarning = formatwarning
        
    def error_or_warning(required, key, value, message):
        message = message.format(key, value)
        if required:
            raise ConfigPathError(message)
        else:
            warnings.warn(message, ConfigPathWarning)
    
    for key, value in config.items():
        is_required = key in schema['required']
        if key.endswith("_dir") or key.endswith("_fp"):
            path = Path(value)
            if not path.exists() and key != "output_dir":
                error_or_warning(
                    is_required, key, value,
                    "Path for '{}' does not exist: '{}'")
                continue
            # 'output_dir' doesn't need to exist at runtime, Snakemake will
            # create it if necessary
            if key.endswith("_dir") and key != "output_dir":
                if not path.is_dir():
                    error_or_warning(
                        is_required, key, value,
                        "Path for '{}' is not a directory: '{}'")
                    continue
            elif key.endswith("_fp"):
                if not path.is_file():
                    if path.is_dir():
                        error_or_warning(
                            is_required, key, value,
                            "'{}' must be a file, not a directory: '{}'")
                        continue
                    else:
                        error_or_warning(
                            is_required, key, value,
                            "Path for '{}' is not a regular file: '{}'")
                        continue

def resolve_paths(config):
    updated_config = config
    for key, value in config.items():
        if key.endswith('_dir') or key.endswith('_fp'):
            updated_config[key] = str(Path(value).expanduser().resolve())
    return updated_config

def create_empty_config(output_dir, samplesheet_fp):
    schema = yaml.load(
        resource_stream("mars", "data/config.schema.yaml").read().decode())
    out =  "# MARS configuration file\n"
    out += "# Created with MARS v{}\n\n".format(__version__)
    required = schema['required']
    for key, value in schema['properties'].items():
        is_required = 'required' if key in required else 'optional'
        default = value.get('default')
        _desc = value['description']
        _type = value['type']
        if key == 'output_dir':
            default = output_dir
        if key == 'samplesheet_fp':
            default = samplesheet_fp
        if default is None:
            default = 'foo #fixme' if _type == "string" else "1 #fixme"
        default = default if default is not None else 'null'
        out += "# {} [{}, {}] \n".format(_desc, _type, is_required)
        out += "{}: {}\n\n".format(key, default)
    return(out)
