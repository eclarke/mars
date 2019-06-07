import yaml
import logging
import warnings
import textwrap
from pathlib import Path
from itertools import chain
from pkg_resources import resource_stream, get_distribution

import pandas as pd
import snakemake.utils
import jsonschema.exceptions
import coloredlogs
from snakemake.exceptions import WorkflowError
from snakemake.io import _load_configfile

__version__ = get_distribution(__name__).version

logger = logging.getLogger(__name__)
_level_styles = coloredlogs.DEFAULT_LEVEL_STYLES
_level_styles['error']={'color':'red', 'bold':True}
_field_styles = coloredlogs.DEFAULT_FIELD_STYLES
_field_styles['levelname']={'color':'green'}
coloredlogs.install(
    level='DEBUG',
    logger=logger,
    style="{",
    fmt="{levelname:>7} {name}: {message}",
    level_styles=_level_styles,
    field_styles=_field_styles
)

def padded_barcodes(samples):
    return [str(b).zfill(2) for b in samples.barcode]

def parse_samples(samplesheet_fp):
    return pd.read_csv(
        samplesheet_fp,
        header=0,
        index_col=False,
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

# def check_assembler_requirements(config, schema):
#     if 'assembler' in config:
#         assembler_reqs = schema.get("assembler_requirements", {})
#         missing = set()
#         for asm in config['assembler']:
#             reqs = assembler_reqs.get(asm, [])
#             missing.update(_check_keys(config, reqs))
#         return _check_keys(config, reqs)

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
    
    @format_checker.checks('file')
    def check_filepath(value):
        path = Path(value)
        return path.is_file() if path.exists() else True

    @format_checker.checks('directory')
    def check_directory(value):
        path = Path(value)
        return path.is_dir() if path.exists() else True
    
    all_validators = dict(Draft4Validator.VALIDATORS)
    all_validators['must_exist'] = path_exists
    
    Validator = validators.create(
        meta_schema=Draft4Validator.META_SCHEMA,
        validators=all_validators)

    validator = Validator(
        schema, resolver=resolver, format_checker = format_checker)
    
    errors = []

    if not isinstance(data, dict):
        for row in data.to_dict('records'):
            print(row)
            for ve in validator.iter_errors(row):
                key = ve.relative_path.pop() if len(ve.relative_path) > 0 else None
                errors.append(MarsValidationError(
                    ve.instance, key, ve.message))
    else:
        for ve in validator.iter_errors(data):
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

def create_config(**kwargs):
    schema = yaml.safe_load(
        resource_stream("mars", "data/config.schema.yaml").read().decode())
    out =  "# MARS configuration file\n"
    out += "# Created with MARS v{}\n\n".format(__version__)
    reqs = schema['required']
    target_reqs = schema['target_requirements']
    # asm_reqs = schema['assembler_requirements']
    for key, value in schema['properties'].items():
        key_required_by = []
        if key in reqs:
            key_required_by.append('all')
        for target in target_reqs:
            if key in target_reqs[target]:
                key_required_by.append(target+' workflow')
        # for asm in asm_reqs:
        #     if key in asm_reqs[asm]:
        #         key_required_by.append(asm + ' assembler')
        req_str = "Required by "+", ".join(key_required_by) if key_required_by else "Optional"
        _desc = value['description']
        _type = value['type']
        if 'enum' in value:
            _type += ", one of "+", ".join(value['enum'])
        elif _type == 'array' and 'items' in value and 'enum' in value['items']:
            _type += ", one or more of "+", ".join(value['items']['enum'])
        helpstr = "# {} ({}). {}.".format(_desc, _type, req_str)
        wrapper = textwrap.TextWrapper(subsequent_indent="# ", width=70)
        helpstr = wrapper.fill(helpstr)
        out += helpstr + '\n'
        default = kwargs.get(key, '')
        if not default:
            out += "#"            
        if value['type'] == 'array' and not isinstance(default, list):
            out += "{}: [{}]\n\n".format(key, default)
        else:
            out += "{}: {}\n\n".format(key, default)
    unused_keys = [k for k in kwargs if k not in schema['properties']]
    return((out, unused_keys))
