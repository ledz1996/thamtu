# thamtu - a tool for inspecting and storing packages informations

When working in a large org or trying to monitoring a large number of packages over thousands of repositories,
it is difficult to track which package is being used in which repository. This tool serves as a package parsing
and tracking tool 

Key components:
- `syft` - https://github.com/anchore/syft
- `mongodb` for storage
    
Supporting languages:
- npm
- java (war, jar, ear, ...)
- ruby (gem)
- php 
- python-pip
- rust
- golang
    
Current working functionality:
- Parsing pure-Git remote repository
- Parsing a single GitLab repository (only grabbing package info files)
- Parsing any visible GitLab repository

## Usage

Use the following command to display all supported commands:

```
python3 thamtu.py --help
```

Environment variables to set:
```
MONGO_HOST
MONGO_USER
MONGO_PASS
MONGO_DB
GITLAB_TOKEN
GITLAB_HOST
```
