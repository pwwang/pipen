"""A second, independent pipen namespace package (generalisation check).

Written to test that the CLI/MCP surface is a property of the framework and
not of any one toy package: a different distribution, a different namespace
name, a different domain, same one-entry-point integration.
"""

from pipen import Proc


class FastaGc(Proc):
    """Compute the GC fraction of a FASTA file

    Input:
        fasta: plain-text FASTA file

    Envs:
        window: unused placeholder kept to exercise env annotations

    Output:
        gc: TSV file with the GC fraction
    """

    input = "fasta:file"
    output = "gc:file:gc.tsv"
    envs = {"window": 0}
    script = """
    awk -v w={{envs.window}} '
        /^>/ { next }
        { for (i = 1; i <= length($0); i++) {
              b = toupper(substr($0, i, 1));
              n++;
              if (b == "G" || b == "C") gc++;
          } }
        END { printf("%d\\t%.4f\\n", n, n ? gc / n : 0); }
      ' {{in.fasta}} > {{out.gc}}
    """
