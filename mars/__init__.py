import sys
import yaml
import warnings
from pathlib import Path
from itertools import chain
from pkg_resources import resource_stream, get_distribution

import pandas as pd
import snakemake.utils
import jsonschema.exceptions
from snakemake.exceptions import WorkflowError
from snakemake.io import _load_configfile

__version__ = get_distribution(__name__).version

def padded_barcodes(samples):
    return [str(b).zfill(2) for b in samples.barcode]

def parse_samples(samplesheet_fp):
    return pd.read_csv(
        samplesheet_fp,
        header=0,
        comment="#",
        sep='\t')

def _check_keys(config, required):
    missing = []
    for rk in required:
        if rk not in config:
            missing.append(rk)
    return missing

def check_universal_requirements(config, schema):
    reqs = schema.get("required", {})
    return _check_keys(config, reqs)

def check_target_requirements(target, config, schema):
    target_reqs = schema.get("target_requirements", {})
    if target:
        reqs = target_reqs[target]
        return _check_keys(config, reqs)

def check_assembler_requirements(config, schema):
    if 'assembler' in config:
        assembler_reqs = schema.get("assembler_requirements", {})
        reqs = assembler_reqs.get(config['assembler'], [])
        return _check_keys(config, reqs)

def detect_target_from_dotgraph(dotgraph, schema):
    targets = schema.get("target_requirements", {})
    for target in targets:
        if 'label = "{}'.format(target) in dotgraph:
            yield target
    
class MarsValidationError(Exception):
    def __init__(self, bad_value, key, reason, line=None):
        self.bad_value = bad_value
        self.key = key
        self.reason = reason
        self.line = line
        super().__init__(reason)

def validate(data, schema):
    from jsonschema import RefResolver, validators, FormatChecker, Draft4Validator
    from urllib.parse import urljoin
    from snakemake.io import _load_configfile

    schemafile = schema
    schema = _load_configfile(schema, filetype="Schema")
    
    resolver = RefResolver(
        urljoin('file:', schemafile), schema,
        handlers={'file': lambda uri: _load_configfile(re.sub("^file://", "", uri))})

    format_checker = FormatChecker()

    def path_exists(validator, properties, instance, schema):
        if properties and not Path(instance).expanduser().exists():
            yield jsonschema.exceptions.ValidationError("{} does not exist".format(instance))
    
    @format_checker.checks('filepath')
    def check_filepath(value):
        path = Path(value)
        return path.is_file() if path.exists() else True

    @format_checker.checks('directory')
    def check_directory(value):
        path = Path(value)
        return path.is_dir() if path.exists() else True
    
    all_validators = dict(Draft4Validator.VALIDATORS)
    all_validators['must_exist'] = path_exists
    
    MyValidator = validators.create(
        meta_schema=Draft4Validator.META_SCHEMA,
        validators=all_validators)

    my_validator = MyValidator(schema, resolver=resolver, format_checker = format_checker)
    
    errors = []

    if not isinstance(data, dict):
        try:
            _validate(data, schemafile)
        except MarsValidationError as e:
            errors.append(e)
    else:
        for ve in my_validator.iter_errors(data):
            key = ve.relative_path.pop() if len(ve.relative_path) > 0 else None
            errors.append(MarsValidationError(
                ve.instance, key, ve.message))
    return errors
        
def _validate(data, schema):
    try:
        snakemake.utils.validate(data, schema)
    except WorkflowError as we:
        ve = we.__context__
        if not isinstance(ve, jsonschema.exceptions.ValidationError):
            raise we
        raise MarsValidationError(
            ve.instance, ve.relative_path.pop(), ve.message) from None


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
            default = ''
        #default = default if default is not None else 'null'
        out += "# {} [{}, {}] \n".format(_desc, _type, is_required)
        if key in required:
            out += "{}: {}\n\n".format(key, default)
        else:
            out += "#{}: {}\n\n".format(key, default)
    return(out)
