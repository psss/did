# Test
## Step
Verify tmt shows help page
```bash
tmt --help
```
## Expect
Text similar to the one bellow is displayed
```
Usage: tmt [OPTIONS] COMMAND [ARGS]...

  Test Management Tool

Options:
...
```
## Test Step
Check that error about missing metadata is sane
```bash
tmt tests ls
```
## Result
```
ERROR  No metadata found in the '.' directory. Use 'tmt init' to get started.
```
## Step
Initialize metadata structure
```bash
tmt init
```
## Expected Result
1. Metadata structure was created
```bash
$ cat .fmf/version
1
```
2. Tool prints advice about next steps
```
To populate it with example content, use --template with mini, base or full.
```

# Test one
## Test Step
description for step 1-1

## Result
description for result 1-1

## Step
description for step 1-2

## Expected Result
description for Expected Result 1-2

# Test two
## Step
description for step 2-1

## Result
description for result 2-1

## Step
description for step 2-2

## Expect
description for Expected Result 2-2

# Cleanup
Optionally remove temporary directory created in the first step
2 line of cleanup
3 line of cleanup
