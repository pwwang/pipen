# Troubleshooting

This guide helps you resolve common issues when using pipen.

## Table of Contents

- [Common Errors](#common-errors)
- [Pipeline Issues](#pipeline-issues)
- [Process Issues](#process-issues)
- [Job and Caching Issues](#job-and-caching-issues)
- [Scheduler Issues](#scheduler-issues)
- [Performance Tips](#performance-tips)
- [Cloud Deployment Issues](#cloud-deployment-issues)
- [Template Issues](#template-issues)

## Common Errors

### `ProcDependencyError`

**Error:**
```
pipen.exceptions.ProcDependencyError: Cycle detected in process dependencies
```

**Cause:** You have created circular dependencies between processes.

**Solution:**
```python
# WRONG: Creates a cycle
class P1(Proc):
    requires = P2

class P2(Proc):
    requires = P1

# CORRECT: Linear dependency
class P1(Proc):
    """First process"""
    pass

class P2(Proc):
    """Second process"""
    requires = P1

class P3(Proc):
    """Third process"""
    requires = P2
```

---

### `ProcInputTypeError`

**Error:**
```
pipen.exceptions.ProcInputTypeError: Unsupported input type 'invalid_type'
```

**Cause:** You specified an invalid input type in the type definition.

**Solution:**
```python
# WRONG
class MyProc(Proc):
    input = "data:invalid_type"

# CORRECT - Valid types are: var, file, dir, files, dirs
class MyProc(Proc):
    input = "data:var"  # In-memory variable
    # or
    input = "data:file"  # Single file
    # or
    input = "data:files"  # Multiple files
```

---

### `ProcInputKeyError`

**Error:**
```
pipen.exceptions.ProcInputKeyError: Input 'invalid_key' not found in process
```

**Cause:** The input key in your script template doesn't match any defined input.

**Solution:**
```python
# WRONG
class MyProc(Proc):
    input = {"filename": "var"}  # Key is 'filename'
    script = "cat {{ in.wrong_name }}"

# CORRECT
class MyProc(Proc):
    input = {"filename": "var"}
    script = "cat {{ in.filename }}"
```

---

### `ProcScriptFileNotFound`

**Error:**
```
pipen.exceptions.ProcScriptFileNotFound: Script file not found: file://missing.py
```

**Cause:** Script file specified with `file://` protocol doesn't exist.

**Solution:**
```python
# Check file exists
from pathlib import Path

script_file = Path("my_script.py")
assert script_file.exists(), f"Script file {script_file} not found"

# Then use in process
class MyProc(Proc):
    script = f"file://{script_file}"
```

---

### `ProcOutputNameError`

**Error:**
```
pipen.exceptions.ProcOutputNameError: No output name specified
```

**Cause:** Output definition is missing or malformed.

**Solution:**
```python
# WRONG
class MyProc(Proc):
    output = "var"  # Missing output name

# CORRECT
class MyProc(Proc):
    output = "result:var"  # 'result' is the name

# Or for files
class MyProc(Proc):
    output = "result:file:output.txt"
```

---

### `NoSuchSchedulerError`

**Error:**
```
pipen.exceptions.NoSuchSchedulerError: Scheduler 'invalid_scheduler' not found
```

**Cause:** Specified scheduler name is incorrect or not installed.

**Solution:**
```python
# Check available schedulers
from pipen.scheduler import SCHEDULERS
print(list(SCHEDULERS.keys()))
# Output: ['local', 'sge', 'slurm', 'ssh', 'container', 'gbatch']

# Use valid scheduler
pipeline = Pipen(scheduler="local")  # or "sge", "slurm", "ssh", "container", "gbatch"
```

---

### `NoSuchTemplateEngineError`

**Error:**
```
pipen.exceptions.NoSuchTemplateEngineError: Template engine 'invalid' not found
```

**Cause:** Specified template engine is not available.

**Solution:**
```python
# Available engines: liquid (default), jinja2, mako
pipeline = Pipen(template="liquid")   # Default
pipeline = Pipen(template="jinja2")  # Install: pip install jinja2
pipeline = Pipen(template="mako")     # Install: pip install mako
```

---

## Pipeline Issues

### Pipeline Fails to Start

**Symptom:** Pipeline doesn't start or hangs indefinitely.

**Possible Causes:**

1. **Process definition errors**
   ```python
   # Check process classes are properly defined
   class MyProc(Proc):
       """Always include docstring"""
       input = "data:var"
       output = "result:var"
       script = "echo {{ in.data }}"
   ```

2. **Dependency issues**
   ```python
   # Verify all required processes are defined
   class P1(Proc):
       pass

   class P2(Proc):
       requires = P1  # P1 must be defined before P2
   ```

3. **Configuration conflicts**
   ```python
   # Check for conflicting configurations
   # Try with minimal config first
   pipeline = Pipen(name="Test")  # Minimal config
   pipeline.run()
   ```

---

### Pipeline Stops Unexpectedly

**Symptom:** Pipeline stops without completing all processes.

**Possible Causes:**

1. **Error strategy is set to 'halt'**
   ```python
   # If a job fails, pipeline stops
   pipeline = Pipen(error_strategy="halt")

   # Change to ignore or retry for robustness
   pipeline = Pipen(error_strategy="retry", num_retries=3)
   ```

2. **Unhandled exception**
   ```python
   # Check the full error message
   # Use verbose logging
   pipeline = Pipen(loglevel="debug")
   pipeline.run()
   ```

---

### Import Errors

**Symptom:** `ImportError` or `ModuleNotFoundError` when importing pipen.

**Solutions:**

1. **Reinstall pipen**
   ```bash
   pip uninstall pipen
   pip install pipen
   ```

2. **Install with all extras**
   ```bash
   pip install pipen[all]  # Installs all optional dependencies
   ```

3. **Check Python version**
   ```bash
   python --version  # Must be 3.9 or higher
   ```

---

## Process Issues

### Process Runs but Produces No Output

**Symptom:** Jobs complete successfully but output files are missing.

**Possible Causes:**

1. **Script doesn't write to output path**
   ```python
   # WRONG - Script writes to wrong location
   script = "echo 'result' > /tmp/output.txt"

   # CORRECT - Write to template output variable
   script = "echo 'result' > {{ out.output_file }}"
   ```

2. **Output path not resolved**
   ```python
   # Debug output paths
   class MyProc(Proc):
       input = "data:var"
       output = "result:file:result.txt"
       script = """
       # Debug input/output
       echo "Input: {{ in.data }}"
       echo "Output: {{ out.result }}"
       echo "Output path: {{ out.result | realpath }}"
       """
   ```

3. **Permission issues**
   ```bash
   # Check write permissions in workdir
   ls -la ~/.pipen/
   chmod +w ~/.pipen/
   ```

---

### Process Input Not Matching Expected Data

**Symptom:** Input values are None or incorrect type.

**Possible Causes:**

1. **Channel data structure mismatch**
   ```python
   # WRONG - Column names don't match
   channel = Channel.create([
       ("value1", "value2", "value3")  # 1 row, 3 columns
   ])
   class MyProc(Proc):
       input = {"wrong_name": "var"}  # Wrong column name

   # CORRECT
   class MyProc(Proc):
       input = {"value1": "var", "value2": "var", "value3": "var"}
   ```

2. **Type mismatch in transform functions**
   ```python
   # Transform input data correctly
   def transform_input(input_data):
       # input_data is a DataFrame row
       return {
           'processed': input_data['value'] * 2,
           'timestamp': str(time.time())
       }

   class MyProc(Proc):
       input = "data:var"
       input_data = transform_input  # Apply transform
   ```

---

## Job and Caching Issues

### Jobs Running with Old Results

**Symptom:** Jobs run but use cached results from previous runs.

**Cause:** Cache signature hasn't changed.

**Solutions:**

1. **Force cache invalidation**
   ```python
   # Delete cache directory
   pipeline = Pipen()
   pipeline.run()
   # Or manually delete workdir
   rm -rf ~/.pipen/MyPipeline/
   ```

2. **Modify input data or script**
   ```python
   # Changing either input or script invalidates cache
   class MyProc(Proc):
       input = "data:var"
       script = "echo '{{ in.data }}' > {{ out.result }}"
   ```

3. **Disable caching temporarily**
   ```python
   # Disable caching for debugging
   pipeline = Pipen(cache=False)
   pipeline.run()
   ```

---

### Cache Not Working

**Symptom:** Jobs rerun even when input hasn't changed.

**Cause:** Signature computation not matching expected behavior.

**Solutions:**

1. **Check signature file**
   ```bash
   # View job signature
   cat ~/.pipen/MyPipeline/MyProc/0/job.signature.toml

   # Should contain:
   # [signature]
   # input_hash = "..."
   # script_hash = "..."
   ```

2. **Enable directory signatures**
   ```python
   # For directory outputs
   class MyProc(Proc):
       input = "indir:dir"
       output = "outdir:dir"
       dirsig = 1  # Enable directory signature
   ```

3. **Check file modification times**
   ```bash
   # View file timestamps
   ls -la input_dir/

   # Cache invalidates if input files are modified
   ```

---

### Jobs Hanging or Failing Intermittently

**Symptom:** Jobs hang or fail randomly.

**Possible Causes:**

1. **Resource limits**
   ```python
   # Reduce parallelization
   pipeline = Pipen(forks=2)  # Lower concurrency

   # Reduce submission batch size
   pipeline = Pipen(submission_batch=4)
   ```

2. **Network issues (for remote schedulers)**
   ```python
   # Increase retry count
   pipeline = Pipen(num_retries=5)
   ```

3. **Memory issues**
   ```python
   # Profile memory usage
   class MyProc(Proc):
       script = """
       # Add memory monitoring
       /usr/bin/time -v echo '{{ in.data }}' > {{ out.result }}'
       """
   ```

---

## Scheduler Issues

### Local Scheduler Issues

**Jobs not running:**

```bash
# Check if any processes are running
ps aux | grep python

# Check workdir permissions
ls -la ~/.pipen/
```

---

### SLURM Issues

**Jobs not submitted:**

```bash
# Check SLURM configuration
sinfo  # View cluster status
squeue -u $USER  # View your jobs

# Test SLURM submission manually
sbatch --test job_script.sh
```

**Common solutions:**

```python
# Set SLURM-specific options
pipeline = Pipen(
    scheduler="slurm",
    scheduler_opts={
        "partition": "compute",
        "time": "01:00:00",
        "mem": "4G"
    }
)
```

---

### SGE Issues

**Jobs not submitted:**

```bash
# Check SGE status
qstat

# Test SGE submission manually
qsub job_script.sh
```

**Common solutions:**

```python
# Set SGE-specific options
pipeline = Pipen(
    scheduler="sge",
    scheduler_opts={
        "q": "all.q",
        "pe": "smp 4"
    }
)
```

---

### Google Cloud Batch Issues

**Jobs not running:**

```bash
# Check Cloud Batch status
gcloud batch jobs list

# Check logs
gcloud batch jobs describe <job-id> --format=json

# Check bucket permissions
gsutil ls gs://your-bucket/
```

**Common solutions:**

```python
# Set GBatch-specific options
pipeline = Pipen(
    scheduler="gbatch",
    scheduler_opts={
        "project": "your-project",
        "region": "us-central1",
        "location": "us-central1"
    }
)

# Ensure cloud paths are correct
from cloudsh import CloudPath
input_path = CloudPath("gs://your-bucket/input/")
```

---

## Performance Tips

### Slow Pipeline Execution

**Solutions:**

1. **Increase parallelization**
   ```python
   # Run more jobs concurrently
   pipeline = Pipen(forks=8)  # Default is 1

   # Increase submission batch size
   pipeline = Pipen(submission_batch=16)  # Default is 8
   ```

2. **Use appropriate scheduler**
   ```python
   # For many small jobs: Local
   pipeline = Pipen(scheduler="local")

   # For large compute jobs: SLURM or SGE
   pipeline = Pipen(scheduler="slurm")

   # For cloud-scale: Google Cloud Batch
   pipeline = Pipen(scheduler="gbatch")
   ```

3. **Optimize data flow**
   ```python
   # Use channel operations effectively
   # Filter data early to reduce job count
   channel = Channel.from_glob("data/*.txt")
   filtered = channel[channel['size'] < 1000]

   # Use expand_dir/collapse_files for file operations
   channel = channel.expand_dir('file')
   ```

4. **Enable caching**
   ```python
   # Caching is enabled by default
   # Ensure it's working
   pipeline = Pipen(cache=True)
   ```

---

### High Memory Usage

**Solutions:**

1. **Reduce job concurrency**
   ```python
   pipeline = Pipen(forks=2)  # Reduce from default
   ```

2. **Stream data instead of loading all**
   ```python
   # Process files individually
   class MyProc(Proc):
       input = "infile:file"
       output = "outfile:file"
       script = """
       # Stream line by line
       while IFS= read -r line; do
           echo "$line" >> {{ out.outfile }}
       done < {{ in.infile }}
       """
   ```

3. **Use batch processing**
   ```python
   # Group files into batches
   channel = Channel.from_glob("data/*.txt", sortby="name")
   # Process multiple files per job
   ```

---

### Disk Space Issues

**Symptom:** Workdir fills up disk space.

**Solutions:**

1. **Change workdir location**
   ```python
   # Use a directory with more space
   pipeline = Pipen(workdir="/scratch/pipen_workdir")
   ```

2. **Clean up old runs**
   ```bash
   # Remove old pipeline runs
   rm -rf ~/.pipen/MyPipeline-*/

   # Keep only cache
   rm -rf ~/.pipen/MyPipeline/*/input
   ```

3. **Use cloud storage for outputs**
   ```python
   # Set output directory to cloud
   pipeline = Pipen(
       outdir="gs://your-bucket/output/",
       export=True  # Mark as export process
   )
   ```

---

## Cloud Deployment Issues

### Authentication Failures

**Symptom:** `AuthenticationError` when accessing cloud resources.

**Solutions:**

```bash
# Authenticate with Google Cloud
gcloud auth login
gcloud auth application-default login

# Check credentials
gcloud auth list
```

```python
# Ensure cloud paths are properly configured
from cloudsh import CloudPath

# Check authentication works
try:
    path = CloudPath("gs://your-bucket/")
    print(list(path.iterdir()))
except Exception as e:
    print(f"Authentication failed: {e}")
```

---

### Cloud Storage Issues

**Symptom:** File operations fail on cloud storage.

**Solutions:**

1. **Use cloudpathlib cache**
   ```bash
   # Set cache directory to local disk
   export CLOUDPATHLIB_LOCAL_CACHE_DIR=/path/to/cache
   ```

2. **Check bucket permissions**
   ```bash
   # Verify bucket access
   gsutil ls gs://your-bucket/
   gsutil acl get gs://your-bucket/
   ```

3. **Use appropriate path types**
   ```python
   from cloudsh import CloudPath, LocalPath

   # Local paths
   local_path = LocalPath("/local/data.txt")

   # Cloud paths
   cloud_path = CloudPath("gs://bucket/data.txt")
   ```

---

### Network Timeouts

**Symptom:** Jobs fail with timeout errors.

**Solutions:**

```python
# Increase retry count for network operations
pipeline = Pipen(num_retries=5)

# Increase timeout (if scheduler supports it)
pipeline = Pipen(
    scheduler="gbatch",
    scheduler_opts={
        "timeout": "3600"  # 1 hour timeout
    }
)
```

---

## Template Issues

### Template Rendering Errors

**Error:**
```
pipen.exceptions.TemplateRenderingError: Failed to render template
```

**Cause:** Invalid template syntax or undefined variables.

**Solutions:**

1. **Check variable names**
   ```python
   # Ensure variables are referenced correctly
   class MyProc(Proc):
       input = {"filename": "var"}
       script = "cat {{ in.filename }}"  # Double braces
   ```

2. **Use correct template syntax**
   ```python
   # Liquid template (default)
   script = """
   Liquid: {{ in.data | upper }}
   """

   # Jinja2 template
   pipeline = Pipen(template="jinja2")
   script = """
   Jinja2: {{ in.data.upper() }}
   """
   ```

3. **Debug template rendering**
   ```python
   # Add debug output
   script = """
   echo "Input data: {{ in.data }}"
   echo "Input type: {{ in.data | type }}"
   echo "Processing..."
   """
   ```

---

### Filter Not Working

**Symptom:** Template filters don't produce expected output.

**Solutions:**

1. **Check filter availability**
   ```python
   # Built-in filters
   script = """
   {{ in.path | basename }}   # Get filename
   {{ in.path | dirname }}    # Get directory
   {{ in.value | upper }}     # Uppercase
   """
   ```

2. **Register custom filters**
   ```python
   def my_filter(value):
       return value.strip().lower()

   pipeline = Pipen(
       template_opts={
           'filters': {'my_filter': my_filter}
       }
   )

   class MyProc(Proc):
       script = "{{ in.data | my_filter }}"
   ```

3. **Debug filter application**
   ```python
   # Test filters in Python first
   result = my_filter("  Test String  ")
   print(result)  # Should be "test string"
   ```

---

## Getting Help

If you encounter an issue not covered here:

1. **Enable debug logging**
   ```python
   pipeline = Pipen(loglevel="debug")
   pipeline.run()
   ```

2. **Check the logs**
   ```bash
   # View pipeline logs
   cat ~/.pipen/MyPipeline/*.log

   # View job logs
   cat ~/.pipen/MyPipeline/*/job.log
   ```

3. **Search existing issues**
   - Check [GitHub Issues](https://github.com/pwwang/pipen/issues)
   - Search for your error message

4. **Create a new issue**
   Include:
   - Full error message and traceback
   - Python version: `python --version`
   - pipen version: `pipen --version`
   - Minimal reproducible example
   - System information: OS, scheduler type

5. **Ask for help**
   - [GitHub Discussions](https://github.com/pwwang/pipen/discussions)
   - [Documentation](https://pwwang.github.io/pipen)

## Further Reading

- [Error Handling](error.md) - Error strategies
- [Configuration](configurations.md) - Pipeline and process configuration
- [Scheduler](scheduler.md) - Scheduler-specific options
- [Architecture](architecture.md) - Internal architecture details
