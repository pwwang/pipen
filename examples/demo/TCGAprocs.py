from pyppl import Proc
pBamToFastq = Proc(desc = 'Convert bam files to fastq files.')
pBamToFastq.input = 'infile:file'
pBamToFastq.output = [
    'fq1:file:{{i.infile | stem}}_1.fq.gz',
    'fq2:file:{{i.infile | stem}}_2.fq.gz']
pBamToFastq.script = '''
# bamtofastq collate=1 exclude=QCFAIL,SECONDARY,SUPPLEMENTARY \
#     filename= {{i.infile}} gz=1 inputformat=bam level=5 \
#     outputdir= {{job.outdir}} outputperreadgroup=1 tryoq=1 \
#     outputperreadgroupsuffixF=_1.fq.gz \
#     outputperreadgroupsuffixF2=_2.fq.gz \
#     outputperreadgroupsuffixO=_o1.fq.gz \
#     outputperreadgroupsuffixO2=_o2.fq.gz \
#     outputperreadgroupsuffixS=_s.fq.gz
touch {{o.fq1}}
touch {{o.fq2}}
'''

pAlignment = Proc(desc = 'Align reads to reference genome.')
pAlignment.input = 'fq1:file, fq2:file'
#                             name_1.fq.gz => name.bam
pAlignment.output = 'bam:file:{{i.fq1 | stem | stem | [:-2]}}.bam'
pAlignment.script = '''
# bwa mem -t 8 -T 0 -R <read_group> <reference> {{i.fq1}} {{i.fq2}} | \
#     samtools view -Shb -o {{o.bam}} -
touch {{o.bam}}
'''

pBamSort = Proc(desc = 'Sort bam files.')
pBamSort.input = 'inbam:file'
pBamSort.output = 'outbam:file:{{i.inbam | basename}}'
pBamSort.script = '''
# java -jar picard.jar SortSam CREATE_INDEX=true INPUT={{i.inbam}} \
#     OUTPUT={{o.outbam}} SORT_ORDER=coordinate VALIDATION_STRINGENCY=STRICT
touch {{o.outbam}}
'''

pBamMerge = Proc(desc = 'Merge bam files.')
pBamMerge.input = 'inbam:file'
pBamMerge.output = 'outbam:file:{{i.inbam | basename}}'
pBamMerge.script = '''
# java -jar picard.jar MergeSamFiles ASSUME_SORTED=false CREATE_INDEX=true \
#     INPUT={{i.inbam}} MERGE_SEQUENCE_DICTIONARIES=false OUTPUT={{o.outbam}} \
#     SORT_ORDER=coordinate USE_THREADING=true VALIDATION_STRINGENCY=STRICT
touch {{o.outbam}}
'''

pMarkDups = Proc(desc = 'Mark duplicates.')
pMarkDups.input = 'inbam:file'
pMarkDups.output = 'outbam:file:{{i.inbam | basename}}'
pMarkDups.script = '''
# java -jar picard.jar MarkDuplicates CREATE_INDEX=true INPUT={{i.inbam}} \
#     OUTPUT={{o.outbam}} VALIDATION_STRINGENCY=STRICT
touch {{o.outbam}}
'''