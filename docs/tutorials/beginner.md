# Your First Pipeline

Welcome to pipen! This tutorial will walk you through creating your first pipeline step by step step.

## What You'll Learn

In this tutorial, you will:
- Understand the basic components of a pipen pipeline
- Create a simple two-process pipeline
- Run the pipeline and inspect the results
- Learn about channels, jobs, and caching

## Prerequisites

Before starting, ensure you have:
- Python 3.9 or higher installed
- pipen installed: `pip install -U pipen`

## Understanding the Basics

### What is a Pipeline?

A **pipeline** is a workflow that processes data through multiple steps. Each step (called a **process**) takes input data, performs some operation, and produces output data.

### What is a Process?

A **process** is a single step in your pipeline that:
- Defines what input it needs
- Specifies what output it produces
- Contains the script to execute
- Can depend on other processes

### What is a Job?

When a pipeline runs, each row of input data becomes a **job**. If your input has 100 items, pipen creates 100 jobs that run independently.

### What is a Channel?

A **channel** is how data flows between processes. It's like a spreadsheet where each row represents a job and each column represents a piece of data that job needs.

---

## Step 1: Create Your First Process

Let's create a simple process that sorts lines in a file.

Create a file called `my_pipeline.py`:

```python
from pipen import Proc

class SortFile(Proc):
    """Sort the contents of a file."""

    # Define input: expects a file path
    input = "infile:file"

    # Provide sample data for testing
    input_data = "/tmp/data.txt"

    # Define output: a file called "sorted.txt"
    output = "outfile:file:sorted.txt"

    # The script to execute
    # {{ in.infile }} will be replaced with the input file path
    # {{ out.outfile }} will be replaced with the output file path
    script = """
    cat {{ in.infile }} | sort > {{ out.outfile }}
    """
```

**Explanation:**

- `class SortFile(Proc)`: Define a process by inheriting from `Proc`
- `input = "infile"`: This process expects one piece of input data named "infile"
- `input_data = "/tmp/data.txt"`: Sample input data (a file path)
- `output = "outfile:file:sorted.txt"`: Output is a file named "sorted.txt"
- `script = """..."""`: The bash script to execute with template variables

---

## Step 2: Create a Second Process

Now let's add a second process that adds line numbers to our sorted file.

Add to `my_pipeline.py`:

```python
class AddLineNumbers(Proc):
    """Add line numbers to each line."""

    # This process depends on SortFile
    requires = SortFile

    # Input is a file (output from SortFile)
    input = "infile:file"

    # Output is a file called "numbered.txt"
    output = "outfile:file:numbered.txt"

    # Script adds line numbers (1-3 in this case)
    script = """
    paste <(seq 1 3) {{ in.infile }} > {{ out.outfile }}
    """
```

**Explanation:**

- `requires = SortFile`: This process runs after SortFile completes
- `input = "infile:file"`: The `:file` type tells pipen this is a file path
- The output from `SortFile` automatically becomes the input to `AddLineNumbers`

---

## Step 3: Define and Run the Pipeline

Now let's put it all together and run our pipeline.

Update `my_pipeline.py`:

```python
from pipen import Proc, run

class SortFile(Proc):
    """Sort the contents of a file."""
    input = "infile"
    input_data = "/tmp/data.txt"
    output = "outfile:file:sorted.txt"
    script = "cat {{ in.infile }} | sort > {{ out.outfile }}"

class AddLineNumbers(Proc):
    """Add line numbers to each line."""
    requires = SortFile
    input = "infile:file"
    output = "outfile:file:numbered.txt"
    script = "paste <(seq 1 3) {{ in.infile }} > {{ out.outfile }}"

# Run the pipeline
if __name__ == "__main__":
    # Create test data
    import os
    os.makedirs("/tmp", exist_ok=True)
    with open("/tmp/data.txt", "w") as f:
        f.write("3\\n2\\n1")

    run("MyFirstPipeline", starts=SortFile)
```

---

## Step 4: Run Your Pipeline

Execute your pipeline:

```bash
python my_pipeline.py
```

You should see output similar to:

```
04-17 16:19:35 I core                   _____________________________________   __
04-17 16:19:35 I core                   ___  __ \___  ____ \___ | |   | |
04-17 16:19:35 I core                  |\/ |  |\/ |   | | |   | |
04-17 16:19:35 I core
04-17 16:19:35 I core                               version: 1.1.7
04-17 16:19:35 I core
04-17 16:19:35 I core    ╔══════════════════════ MYFIRSTPIPELINE ════════════════════════╗
04-17 16:19:35 I core    ║ My first pipeline                                                ║
04-17 16:19:35 I core    ╚═══════════════════════════════════════════════════════════════╝
04-17 16:19:35 I core    # procs         : 2
04-17 16:19:35 I core    profile         : default
04-17 16:19:35 I core    outdir          : /path/to/cwd/MyFirstPipeline-output
04-17 16:19:35 I core    cache           : True
04-17 16:19:35 I core    dirsig          : 1
04-17 16:19:35 I core    error_strategy  : ignore
04-17 16:19:35 I core    forks           : 1
04-17 16:19:35 I core    lang            : bash
04-17 16:19:35 I core    loglevel        : info
04-17 16:19:35 I core    num_retries     : 3
04-17 16:19:35 I core    scheduler       : local
04-17 16:19:35 I core    submission_batch: 8
04-17 16:19:35 I core    template        : liquid
04-17 16:19:35 I core    workdir         : /path/to/cwd/.pipen/MyFirstPipeline
04-17 16:19:35 I core    Initializing plugins ...
04-17 16:19:36 I core
04-17 16:19:36 I core    ╭─────────────────────────────── SortFile ────────────────────────────────╮
04-17 16:19:36 I core    │ Sort the contents of a file.                                      │
04-17 16:19:36 I core    ╰─────────────────────────────────────────────────────────────────────────╯
04-17 16:19:36 I core    SortFile: Workdir: '/path/to/cwd/.pipen/MyFirstPipeline/SortFile'
04-17 16:19:36 I core    SortFile: <<< [START]
04-17 16:19:36 I core    SortFile: >>> ['AddLineNumbers']
04-17 16:19:36 I core    SortFile: >>> [END]
04-17 16:19:36 I core
04-17 16:19:36 I core    ╭═══════════════════════ AddLineNumbers ════════════════════════╮
04-17 16:19:36 I core    ║ Add line numbers to each line.                                     ║
04-17 16:19:36 I core    ╚═════════════════════════════════════════════════════════════╝
04-17 16:19:36 I core    AddLineNumbers: Workdir: '/path/to/cwd/.pipen/MyFirstPipeline/AddLineNumbers'
04-17 16:19:36 I core    AddLineNumbers: <<< ['SortFile']
04-17 16:19:36 I core    AddLineNumbers: >>> [END]

             MYFIRSTPIPELINE: 100%|██████████████████████████████| 2/2 [00:00<00:00, 0.35 procs/s]
```

**What happened:**

1. Pipen initialized the pipeline with 2 processes
2. SortFile ran first, created `sorted.txt`
3. AddLineNumbers ran second, used `sorted.txt` as input, created `numbered.txt`
4. Progress bar showed completion of both processes
5. Final output saved to `MyFirstPipeline-output/` directory

---

## Step 5: Inspect the Results

Check your output:

```bash
cat MyFirstPipeline-output/AddLineNumbers/numbered.txt
```

Expected output:

```
1       1
2       2
3       3
```

You can also check the intermediate output:

```bash
cat .pipen/MyFirstPipeline/SortFile/0/output/sorted.txt
```

Expected output:

```
1
2
3
```

---

## Understanding Channels and Jobs

Let's modify our pipeline to process multiple files at once.

Update `my_pipeline.py`:

```python
from pipen import Proc, run

class SortFile(Proc):
    """Sort the contents of a file."""
    input = "infile"
    # Multiple input files
    input_data = [
        "/tmp/data1.txt",
        "/tmp/data2.txt",
        "/tmp/data3.txt"
    ]
    output = "outfile:file:sorted.txt"
    script = "cat {{ in.infile }} | sort > {{ out.outfile }}"

class AddLineNumbers(Proc):
    """Add line numbers to each line."""
    requires = SortFile
    input = "infile:file"
    output = "outfile:file:numbered.txt"
    script = "paste <(seq 1 3) {{ in.infile }} > {{ out.outfile }}"

if __name__ == "__main__":
    # Create test data
    import os
    os.makedirs("/tmp", exist_ok=True)
    for i in range(1, 4):
        with open(f"/tmp/data{i}.txt", "w") as f:
            f.write(f"{4-i}\\n{i-1}\\n{i-2}")

    run("MyFirstPipeline", starts=SortFile)
```

Now run it again:

```bash
python my_pipeline.py
```

You'll see **3 jobs** run for SortFile (one for each input file), and then 3 jobs run for AddLineNumbers.

**Key concept:** Each row in the input channel becomes a separate job that runs independently.

---

## Step 6: Understanding Caching

pipen automatically caches results to avoid recomputing.

Run the pipeline again without changing anything:

```bash
python my_pipeline.py
```

You'll see:

```
SortFile: >>> ['AddLineNumbers']
SortFile: >>> [END]
SortFile: CACHED   <--- Notice "CACHED" instead of running
```

The jobs don't run again because the output already exists and inputs haven't changed.

**To force re-running:**

Delete the workdir:

```bash
rm -rf .pipen/MyFirstPipeline
python my_pipeline.py
```

Now all jobs will run again.

---

## Step 7: More Complex Input Data

Let's use structured input data with multiple columns.

Create `structured_pipeline.py`:

```python
from pipen import Proc, run, Channel

class ProcessSamples(Proc):
    """Process sample files with metadata."""

    # Channel input with multiple columns
    input_data = Channel.create([
        ("sample1.txt", "control", "rep1"),
        ("sample2.txt", "control", "rep2"),
        ("sample3.txt", "treatment", "rep1"),
        ("sample4.txt", "treatment", "rep2"),
    ])

    input = [
        "filename:file",
        "condition:var",
        "replicate:var",
    ]

    output = "result:file:result.txt"

    script = """
    echo "{{ in.condition }} - {{ in.filename }} ({{ in.replicate }})" > {{ out.result }}
    """

if __name__ == "__main__":
    # Create test files
    import os
    os.makedirs("/tmp", exist_ok=True)
    for filename, _, _ in [
        ("sample1.txt", "control", "rep1"),
        ("sample2.txt", "control", "rep2"),
        ("sample3.txt", "treatment", "rep1"),
        ("sample4.txt", "treatment", "rep2"),
    ]:
        with open(f"/tmp/{filename}", "w") as f:
            f.write("sample data")

    run("StructuredPipeline", starts=ProcessSamples)
```

**Explanation:**

- `Channel.create([...])`: Creates a channel where each tuple is a row
- Input has 3 columns: `filename`, `condition`, `replicate`
- The script can access all three columns via template variables
- Creates 4 jobs, one for each input tuple

---

## Common Patterns

### Pattern 1: Multiple Files from Directory

```python
from pipen import Proc, run, Channel

class ProcessFiles(Proc):
    """Process all files in a directory."""

    # Use glob to find all .txt files
    input_data = Channel.from_glob("/tmp/*.txt", sortby="name")

    input = "infile:file"
    output = "outfile:file:processed.txt"
    script = "cat {{ in.infile }} > {{ out.outfile }}"

run("GlobPipeline", starts=ProcessFiles)
```

### Pattern 2: Conditional Execution

```python
from pipen import Proc, run

class ConditionalProcess(Proc):
    """Process files based on condition."""

    input = [
        "infile:file",
        "process:var",  # 'skip' or 'process'
    ]

    output = "outfile:file:output.txt"

    script = """
    if [ "{{ in.process }}" == "process" ]; then
        cat {{ in.infile }} > {{ out.outfile }}
    else
        echo "Skipped"
    fi
    """
```

### Pattern 3: Error Handling

```python
from pipen import Proc, run

class SafeProcess(Proc):
    """Process with error handling."""

    input = "data:var"
    output = "result:file:result.txt"

    script = """
    # Exit with error code 1 if data is empty
    if [ -z "{{ in.data }}" ]; then
        echo "Error: Empty data"
        exit 1
    fi
    echo "Processing {{ in.data }}" > {{ out.result }}
    """

run("SafePipeline", starts=SafeProcess, error_strategy="retry")
```

---

## Next Steps

Congratulations! You've created your first pipeline. Now you can:

- Read [Basics](../basics.md) for more on pipeline structure
- Learn about [Channels](../channels.md) for data flow
- Explore [Configurations](../configurations.md) to customize your pipeline
- Check the [Examples](../examples.md) for more complex patterns
- Read the [API Reference](../api/pipen.md) for detailed documentation

## Troubleshooting

**Problem:** Pipeline doesn't run

**Solution:** Check that:
- Python 3.9+ is installed: `python --version`
- pipen is installed: `pip show pipen`
- Input files exist: `ls /tmp/data.txt`

**Problem:** Jobs fail with "command not found"

**Solution:** Make sure:
- Script uses correct bash syntax
- Commands available in your PATH
- Template variables are properly formatted: `{{ in.varname }}`

**Problem:** Output files not created

**Solution:**
- Check script writes to output path: `{{ out.output_var }}`
- Verify output directory is writable
- Check job logs in `.pipen/<pipeline>/<process>/*/job.log`

For more help, see the [Troubleshooting Guide](../troubleshooting.md).
