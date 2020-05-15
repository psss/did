# Setup
1. Install tmt
```bash
sudo dnf install -y tmt-all
```
2. Create and use a brand new git repo
```bash
cd `mktemp -d`
git init
```
# Test
## Step
Verify tmt show help page
```bash
tmt --help
```
## Expect
Text similar to the one bellow is displayed
```
Usage: tmt [OPTIONS] COMMAND [ARGS]...

  Test Management Tool

Options:
....
```
## Step
Check that error about missing metadata is sane
```bash
tmt tests ls
```
## Expect
```
ERROR  No metadata found in the '.' directory. Use 'tmt init' to get started.
```
## Step
Initialize metadata structure
```bash
tmt init
```
## Expect
1. Metadata structure was created
```bash
$ cat .fmf/version
1
```
2. Tool prints advice about next steps
```
To populate it with example content, use --template with mini, base or full.
```

# Cleanup
Optionally remove temporary directory created in the first step
