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

> If a sample was split among multiple barcodes, i.e. for technical replicates, you can choose to give those barcodes the same sample label.
> MARS will concatenate the reads from all barcodes belonging to the same sample label during assembly.

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

Once you've created the sample sheet, use `mars init` to create a config file template.
`mars init` requires two arguments:

- `output_dir`: the directory to store all output from MARS
- `samplesheet_fp`: the path to the sample sheet you created above.

By default it writes the config file to the screen.
Use redirection (`>`) to pipe it to a file to save it.

```bash
mars init --output_dir mars_output --samplesheet_fp samples.tsv > project_name.yaml
```

MARS has a lot of configuration options, which are described by a comment over each option.
Options that are not required by all rules are commented-out by default. 

Steps that require certain configuration options will let you know during execution.
Edit the config file, uncomment that option by removing the `#` and specify a value.

Other options have reasonable defaults specified, like the number of threads given to any program.
To override the defaults, uncomment the corresponding `[program]_threads: ` option and specify a number.

> *Config Validation:* Config options that end in `_dir` or `_fp` must be paths to valid directories or files, respectively.
> MARS will resolve any relative paths against the directory it's executed from, and stop if any paths besides `output_dir` do not exist.
> In addition, some config options' values must be numbers (as noted in the config file).
> MARS will complain if they're invalid, saving you the headache of debugging some random Snakemake error down the line.

### Running

Finally, running MARS is comparatively simple. Just type:

```bash
mars run my_project.yaml [task name] [any Snakemake options]
```

The tasks currently available are:

- `process_all`: Basecalls, demultiplexes, and trims adapters from a set of .fast5 files using Guppy or Albacore.
- `canu_assemble_all`: Performs _de novo_ assembly of all samples using Canu.
- `rebaler_assemble_all`: Performs reference-based assembly of all samples using Rebaler.
- `unicycler_assemble_all`: Performs _de novo_ assembly of all samples using Unicycler.
- `{assembler}_polish: Polishes any of the above assemblies using Nanopolish.

For instance, a typical user may start by processing their fast5 files.
MARS can do this with either Albacore or Guppy.
Specify which to use in your config file under `basecaller`, along with the path to your fast5 files, then run:

```bash
mars run project.yaml process_all
```

Upon completion, you may then wish to assemble against a reference genome.
Edit your config file to provide a path to your reference genome in `ref_genome_fp` and then run:

```bash
mars run project.yaml rebaler_assemble_all
```

or

```bash
mars run project.yaml rebaler_polish
```

#### Snakemake options

Since MARS calls Snakemake to execute each step, you can pass any Snakemake options to `mars run` and they will be transparently passed to Snakemake during execution.

MARS automatically calls `--use-conda` as it is required for dependency management.




