"""Toy scientific namespace used to demonstrate pipen's agent-facing surface.

Declaring the process classes below is the *entire* integration: installing
this package makes them available as

  * CLI sub-commands   -- ``pipen run demo_ns <Proc> ...``   (pipen-cli-run)
  * discovery + run MCP tools -- ``get_processes`` / ``run_process`` (pipen-mcp)

No argument parsing, no JSON schema, no server code is written by hand here.
"""

from pipen import Proc


class FastqStats(Proc):
    """Read-length statistics of a paired-end FASTQ sample

    Input:
        r1: gzipped R1 FASTQ file of the sample
        r2: gzipped R2 FASTQ file of the sample

    Envs:
        min_length: Reads shorter than this many bases are not counted
        sample_id: Label written into the first column of the output table

    Output:
        stats: TSV table of per-sample read-length statistics
    """

    input = "r1:file, r2:file"
    output = "stats:file:read_stats.tsv"
    envs = {"min_length": 0, "sample_id": "sample"}
    script = """
    zcat {{in.r1}} {{in.r2}} \\
      | awk -v min={{envs.min_length}} -v sid={{envs.sample_id}} '
          NR % 4 == 2 {
              n++;
              len += length($0);
              if (length($0) > max) max = length($0);
              if (length($0) >= min) kept++;
          }
          END {
              printf("%s\\t%d\\t%d\\t%d\\t%.1f\\n", sid, n, kept, max, len / n);
          }
        ' > {{out.stats}}
    """


class CountReads(Proc):
    """Count the reads in a single FASTQ file

    Input:
        fastq: gzipped FASTQ file to count

    Envs:
        sample_id: Label written into the output table

    Output:
        counts: TSV table holding the read count
    """

    input = "fastq:file"
    output = "counts:file:read_counts.tsv"
    envs = {"sample_id": "sample"}
    script = """
    zcat {{in.fastq}} \\
      | awk -v sid={{envs.sample_id}} '
          NR % 4 == 1 { n++ }
          END { printf("%s\\t%d\\n", sid, n); }
        ' > {{out.counts}}
    """
