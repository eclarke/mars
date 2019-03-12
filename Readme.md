# MARS: MinION Assembly and Reporting System

Snakemake-based pipeline for quality control reporting and assembly (both _de novo_ and reference-based) from a MinION run.

_Warning: very much in active development._

## Requirements:

- conda
- python3
- albacore or guppy (your choice) from Oxford Nanopore

## Installation

It's highly recommended to install this into a conda environment, but not required.
Conda is required for downstream steps using Snakemake, but not to execute or install MARS.

```bash
git clone https://github.com/eclarke/mars
cd mars
pip install .
```

## Usage

The general process is to create a config file for your project/run using `mars init` and then execute the pipeline using `mars run`.

### Init

#### Create a sample sheet

To begin, MARS needs a sample sheet in tab-delimited format with two columns: `barcode` and `sample_label`.
`barcode` should contain only numbers between 1-96, and each barcode can only appear once.
`sample_label` should contain no spaces and a sample label can appear multiple times.
MARS will yell at you if you violate either of these rules.
Other columns are currently ignored and can be used for whatever you want.

**Technical replicates:**
If a sample was split among multiple barcodes, you can choose to give those barcodes the same sample label.
MARS will pool the reads from all barcodes belonging to the same sample label during assembly steps.

**Run metadata:**
Additional run info can be encoded in the header in lines starting with '#' using the format `# key[tab]value`.
(The key-value pairs are tab-separated so you can enter them in adjacent cells in Excel, etc and export as tab-separated list.)
These will be automatically parsed as key:value pairs and added to the configuration file.

Here is an example sample sheet:

```
# flowcell	FLO-MIN106
# kit	SQK-RBK004
# run_number	0
barcode sample_label	description
1       s1	sample 1
2	s2	sample 2
3	s3	sample 3
```

I've made a validating sample sheet template available [here](https://docs.google.com/spreadsheets/d/1KsxHezzwVZjvFzjsX4kHZ6y9_uGRNU3SoDTMNqmcNWs/edit?usp=sharing).
Choose File -> Make a copy... to save it to your own Drive for later use.
After filling it out, choose File -> Download as... -> Tab-separated values and transfer it to the server running MARS.


#### Create a config file

Once you've created the sample sheet, use `mars init` to create an empty config file.
Each config value has a description above it, including which MARS workflows its required by.
To prefill certain pairs during creation, specify them as `key:value` pairs (note: it's a good idea to use absolute paths here).

Creating a totally empty config file:
```bash
mars init
```

Pre-fill important info and write it to `project.marsconfig`:
```bash
mars init --output project.marsconfig output_dir:/project/mars_out samplesheet_fp:/project/samples.tsv
```

**Config Validation:**
Config options that end in `_dir` or `_fp` must be paths to valid directories or files, respectively.
MARS will resolve any relative paths against the directory it's executed from, and stop if any paths besides `output_dir` do not exist.
In addition, some config options' values must be numbers (as noted in the config file).
MARS will complain if they're invalid, saving you the headache of debugging some random Snakemake error down the line.

### Running

Running MARS is straightforward. Just type:

```bash
mars run my_project.yaml <workflow> [any Snakemake options]
```

MARS will give you a helpful error message if any of the config values required for the workflow are not specified in the config file.

The workflows currently available are:

- `process_all`: Basecalls, demultiplexes, and trims adapters from a set of .fast5 files using the specified basecaller.
- `assemble_all`: Assembles each sample using the specified assembler.
- `polish_all`: Polishes each sample assembly using Nanopolish.

Currently the supported basecallers are:

- `guppy`
- `albacore`

Supported assemblers include:

- `canu`
- `unicycler`
- `rebaler`

Specify the desired basecaller and/or assembler in the config file.

#### Snakemake options

Since MARS calls Snakemake to execute each step, you can pass any Snakemake options to `mars run` and they will be transparently passed to Snakemake during execution.

MARS automatically calls `--use-conda` as it is required for dependency management.




