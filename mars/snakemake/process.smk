#
# MARS Pre-processing Workflow
# ----------------------------------------------------------------------
#
# Basecalls, demultiplexes and filters .fast5 files, and produces
# summary reports at both the run and barcode level.

from mars import padded_barcodes

localrules: process, process_all, gather_guppy_fastqs, gather_albacore_fastqs

proc_output_dir = output_dir + 'process/'
proc_working_dir = working_dir + 'process/'
proc_reports_dir = reports_dir + 'process/'

barcodes = expand('barcode{bc}', bc=padded_barcodes(samples)) + ['unclassified']

rule basecall_guppy:
    output:
        summary = proc_reports_dir + 'guppy/sequencing_summary.txt'
    threads:
        config.get('process_threads', 8)
    params:
        fast5_dir = config.get('fast5_dir'),
        flowcell = config.get('flowcell'),
        kit = config.get('kit'),
        out_dir = proc_working_dir + 'guppy/workspace',
        prefix_opt = config.get('guppy_prefix_opt', '')
    shell:
        """
        {params.prefix_opt} \
        guppy_basecaller \
        --input_path {params.fast5_dir} \
        --save_path {params.out_dir} \
        --flowcell {params.flowcell} \
        --kit {params.kit} \
        --recursive \
        --num_callers {threads} && \
        cp {params.out_dir}/sequencing_summary.txt {output.summary}
        """

rule demux_guppy:
    input:
        summary = rules.basecall_guppy.output.summary
    output:
        out_dir = directory(expand(
            rules.basecall_guppy.params.out_dir + '/{barcode}',
            barcode = barcodes)),
        summary = proc_reports_dir + 'guppy/barcoding_summary.txt'
    threads:
        config.get('basecaller_threads', 8)
    params:
        fastq_dir = rules.basecall_guppy.params.out_dir,
        config_opt = (
            '--config ' + config['guppy_barcoder_cfg_fp']
            if config.get('guppy_barcoder_cfg_fp') else ''),
        prefix_opt = config.get('guppy_prefix_opt', '')
    shell:
        """
        {params.prefix_opt} \
        guppy_barcoder \
        --input_path {params.fastq_dir} \
        --save_path {params.fastq_dir} \
        --worker_threads {threads} \
        {params.config_opt} && \
        cp {params.fastq_dir}/barcoding_summary.txt {output.summary}
        """

rule gather_guppy_fastqs:
    '''Cats and gzips Guppy-demuxed fastq files.'''
    input:
        rules.basecall_guppy.params.out_dir+'/{barcode}'
    output:
        proc_working_dir + 'guppy/{barcode}.fastq.gz'
    shell:
        "cat {input}/*.fastq | gzip > {output}"

rule basecall:
    input:
        lambda wc: expand(
            proc_working_dir + '/guppy/{barcode}.fastq.gz',
            barcode = expand('barcode{bc}', bc=padded_barcodes(samples.loc[samples['sample_label'] == wc.sample])))
    output:
        proc_output_dir + 'unfiltered/{sample}.fastq.gz'
    shell:
        """cat {input} > {output}"""
        
rule quality_filter:
    input:
        rules.basecall.output
    output:
        proc_output_dir + 'filtered/{sample}.fastq.gz'
    params:
        min_length = config.get("filt_min_length", 1000),
        keep_percent = (
            ('--keep_percent ' + str(config.get("filt_keep_percent")))
            if "filt_keep_percent" in config else ''),
        target_bases = (
            ('--target_bases ' + str(config.get("filt_target_bases")))
            if "filt_target_bases" in config else ''),
    conda:
        resource_filename("mars", "snakemake/envs/processing.yaml")        
    shell:
        """
        filtlong \
        --min_length {params.min_length} \
        {params.keep_percent} \
        {params.target_bases} \
        {input} | gzip > {output}
        """

rule assess_run_nanoplot:
    input:
        proc_reports_dir + 'sequencing_summary.txt'
    output:
        directory(proc_reports_dir + 'nanoplot')
    threads:
        config.get('nanoplot_threads', 8)
    conda:
        resource_filename("mars", "snakemake/envs/processing.yaml")
    shell:
        """
        NanoPlot --threads {threads} --summary {input} --outdir {output} --plots hex dot pauvre
        """

rule assess_run_nanocomp:
    input:
        expand(
            proc_working_dir + '/{barcode}.fastq.gz', barcode = barcodes)
    output:
        directory(proc_reports_dir + 'nanocomp')
    params:
        names = expand('{barcode}', barcode=barcodes),
        prefix_opt = (
            '--prefix ' + config.get('project_name')
            if 'project_name' in config
            else '')
    threads:
        config.get('nanocomp_threads', 8)
    conda:
        resource_filename("mars", "snakemake/envs/processing.yaml")
    shell:
        """
        NanoComp \
        --fastq {input} \
        --names {params.names} \
        --threads {threads} \
        {params.prefix_opt} \
        --outdir {output} 
        """
        
rule process:
    input:
        filtered=rules.quality_filter.output,
        unfiltered=rules.basecall.output
        
rule process_all:
    message: "Fastq files are in {}; run reports are in {}".format(proc_output_dir, proc_reports_dir)
    input:
        fastqs = expand(rules.process.input, sample=list(samples.sample_label)),
        seq_summary = proc_reports_dir + 'sequencing_summary.txt',
        nanoplot_report = rules.assess_run_nanoplot.output,
        nanocomp_report = rules.assess_run_nanocomp.output

