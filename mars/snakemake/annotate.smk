
localrules: annotate_all, load_rgi_db

ann_output_dir = output_dir + 'annotations/'
ann_working_dir = working_dir + 'annotations/'
ann_reports_dir = reports_dir + 'annotations/'

rule load_rgi_db:
    message:
        (
            "**NOTE**: You MUST install RGI v5 manually into this environment! "
            "\n1. Look for the line that begins 'Activating conda environment: [env path]'"
            "\n2. Activate the environment with `conda activate [env path]`"
            "\n3. Download RGI v5 and install into this environment: "
            "\n\thttps://github.com/arpcard/rgi#install-rgi-from-project-root"
            "\n\t(All dependencies are installed already)"
            "\n4. Confirm you can execute the command `rgi`."
            "\n5. Type `conda deactivate` and continue with MARS"
        )
    output:
        touch(ann_working_dir + '.rgi_loaded')
    params:
        rgi_card_fp = config.get('rgi_card_fp', '')
    conda:
        resource_filename("mars", "snakemake/envs/rgi5.yaml")
    shell:
        (
            "rgi load "
            "-i {params.rgi_card_fp} "
            "--local"
        )

rule annotate_rgi:
    input:
        contigs=rules.assemble.input,
        db_load_flag=rules.load_rgi_db.output
    output:
        ann_output_dir + 'rgi5/{assembler}/{sample}.txt'
    params:
        out_prefix = ann_output_dir + 'rgi5/{assembler}/{sample}'
    threads:
        config.get('annotation_threads', 8)
    conda:
        resource_filename("mars", "snakemake/envs/rgi5.yaml")
    shell:
        (
            "rgi main "
            "--local "
            "--input_sequence {input.contigs} "
            "--output_file {params.out_prefix} "
            "--input_type contig "
            "-a diamond "
            "-n {threads} "
            "--low_quality --clean"
        )

rule rgi_heatmap:
    input:
        expand(
            rules.annotate_rgi.output,
            assembler='{assembler}',
            sample=list(samples.sample_id))
    output:
        directory(ann_reports_dir + 'rgi5/{assembler}')
    params:
        input_dir = ann_output_dir + 'rgi5/{assembler}',
        output = ann_reports_dir + 'rgi5/{assembler}/heatmap'
    shell:
        (
            "mkdir -p {output} && "
            "rgi heatmap "
            "-i {params.input_dir} "
            "-cat gene_family "
            "-o {params.output}"
        )

        
rule annotate_all:
    input:
        annotations=expand(
            rules.annotate_rgi.output,
            assembler=config.get('assembler', ''),
            sample=list(samples.sample_id)),
        heatmaps=expand(
            rules.rgi_heatmap.output,
            assembler=config.get('assembler', ''))
    
