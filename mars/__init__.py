from pathlib import Path
from itertools import chain
from pkg_resources import resource_stream
import yaml

import pandas as pd

def padded_barcodes(samples):
    return [b.zfill(2) for b in samples.barcode]

def parse_samplesheet(sample_fp):
    return pd.read_csv(sample_fp, dtype=str, sep='\t')

def create_empty_config(project_name):
    schema = yaml.load(
        resource_stream("mars", "data/config.schema.yaml").read().decode())
    out = format("# MARS configuration file for project '{}'\n\n".format(project_name))
    required = schema['required']
    for key, value in schema['properties'].items():
        is_required = 'required' if key in required else 'optional'
        _desc = value['description']
        _type = value['type']
        out += "## {} [{}, {}] \n".format(_desc, _type, is_required)
        out += "{}: \n\n".format(key)
    return(out)
