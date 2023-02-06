import typer
from git_utils import GitUtil
from gitlab_utils import GitLabUtil
from urllib.parse import urlparse
from rich.console import Console
from rich.table import Table
from rich.json import JSON
from pymongo import MongoClient
from git import Repo
import warnings
from alive_progress import alive_bar
import gitlab
import tempfile
import os
import json
from rich import print


app = typer.Typer()
warnings.filterwarnings('ignore')
if os.getenv("GITLAB_TOKEN") is not None and os.getenv("GITLAB_TOKEN") != "":
    if os.getenv("GITLAB_HOST") is None or os.getenv("GITLAB_HOST") == "":
        gl = gitlab.Gitlab('https://gitlab.com/', os.getenv("GITLAB_TOKEN"))
    else:
        gl = gitlab.Gitlab('https://{}/'.format(os.getenv("GITLAB_HOST")), os.getenv("GITLAB_TOKEN"))
else:
    gl = None

if os.getenv("MONGO_HOST") is not None and os.getenv("MONGO_HOST") != "":
    mongo_host = os.getenv("MONGO_HOST")
else:
    mongo_host = "localhost"
    
if os.getenv("MONGO_USER") is not None and os.getenv("MONGO_USER") != "":
    mongo_user = os.getenv("MONGO_USER")
else:
    mongo_user = "user"
    
if os.getenv("MONGO_PASSWORD") is not None and os.getenv("MONGO_PASSWORD") != "":
    mongo_pass = os.getenv("MONGO_PASSWORD")
else:
    mongo_pass = "password"
    
if os.getenv("MONGO_DB") is not None and os.getenv("MONGO_DB") != "":
    mongo_db = os.getenv("MONGO_DB")
else:
    mongo_db = "thamtu"

db = MongoClient(mongo_host,
                username=mongo_user,
                password=mongo_pass,
                authMechanism='SCRAM-SHA-256')[mongo_db]

@app.command(short_help='analyze a git repository')
def add_git(remote_path: str):
    print("Analyzing git repo [bold green]{}[/bold green]".format(remote_path))
    with tempfile.TemporaryDirectory() as tmp_dir:
        git_repo = Repo.clone_from(remote_path, tmp_dir)
        git_analyzed_repo = GitUtil(remote_path, "", git_repo, tmp_dir)
        git_analyzed_repo.get_repository()
        git_analyzed_repo.find_files()
        git_analyzed_repo.put_to_db(db)
        
@app.command(short_help='analyze a gitlab repository')
def add_gitlab(remote_path: str):
    print("Analyzing GitLab repo [bold green]{}[/bold green]".format(remote_path))
    path = urlparse(remote_path).path.replace(".git","")
    gitlab_repo = gl.projects.get(path[1:])
    if db.repositories.find_one({"remote_path": gitlab_repo.web_url, "commit": gitlab_repo.commits.list(ref_name=gitlab_repo.default_branch)[0].id}) == None:
        gitlab_analyzed_repo = GitLabUtil(remote_path, "", gitlab_repo)
        gitlab_analyzed_repo.get_repository()
        gitlab_analyzed_repo.find_files()
        gitlab_analyzed_repo.put_to_db(db)

@app.command(short_help='analyze a list of gitlab repository, syntax: add-gitlab-list <file_path(a list of gitlab repositories)>')
def add_gitlab_list(file_path: str):
    txt_file = open(file_path, "r")
    content_list = txt_file.readlines()
    error_repos = []
    typer.echo(f"Analyzing {len(content_list)} GitLab repo")
    with alive_bar(len(content_list), ctrl_c=False, title=f'Analyzing {len(content_list)} projects') as bar:
        for remote_path in content_list:
            bar.text = "-> Analyzing repo: {}, ...".format(remote_path)
            try:
                path = urlparse(remote_path).path.replace(".git","")
                gitlab_repo = gl.projects.get(path[1:])
                if db.repositories.find_one({"remote_path": gitlab_repo.web_url, "commit": gitlab_repo.commits.list(ref_name=gitlab_repo.default_branch)[0].id}) == None:
                    gitlab_analyzed_repo = GitLabUtil(remote_path, "", gitlab_repo)
                    gitlab_analyzed_repo.get_repository()
                    gitlab_analyzed_repo.find_files()
                    gitlab_analyzed_repo.put_to_db(db)
            except:
                error_repos.append(remote_path)
            finally:
                bar()
    if(len(error_repos) != 0):
        print("[bold red]Error[/bold red] running the following repos:")
        for error_repo in error_repos:
            print("- [bold green]{}[/bold green]".format(error_repo))


@app.command(short_help='analyze all visible gitlab repository')
def add_gitlab_all():
    typer.echo(f"Analyzing all visible GitLab repo")
    all_projects = gl.projects.list(all=True)
    error_repos = []
    with alive_bar(len(all_projects), ctrl_c=False, title=f'Analyzing {len(all_projects)} projects') as bar:
        for project in all_projects:
            bar.text = "-> Analyzing repo: {}, ...".format(project.web_url)
            try:
                if db.repositories.find_one({"remote_path": project.web_url, "commit": project.commits.list(ref_name=project.default_branch)[0].id}) == None:
                    gitlab_analyzed_repo = GitLabUtil(project.web_url, "", project)
                    gitlab_analyzed_repo.get_repository()
                    output, err = gitlab_analyzed_repo.find_files()
                    if err is not None:
                        error_repos.append(project.web_url)
                        continue
                    output, err = gitlab_analyzed_repo.put_to_db(db)
                    if err is not None:
                        error_repos.append(project.web_url)
                        continue
            except:
                error_repos.append(project.web_url)
            finally:
                bar()
    if(len(error_repos) != 0):
        print("[bold red]Error[/bold red] running the following repos:")
        for error_repo in error_repos:
            print("- [bold green]{}[/bold green]".format(error_repo))
    

@app.command(short_help='query packages, syntax: query <ptype:npm/rust/golang/java/php/pip/ruby> <package_name>')
def query(ptype: str, package_name: str):
    records = db.packages.find({"type": ptype, "name": package_name})
    table = Table(title="Query result for package {}:{}".format(ptype, package_name),highlight=True)

    table.add_column("Version", justify="left", style="red", no_wrap=False)
    table.add_column("Metadata", justify="left", style="cyan")
    table.add_column("Repositories", style="magenta")
    for rec in records:
        repo_string = ""
        for repository in rec['repositories']:
            repo_string += repository['remote_path'] + "#" + repository['commit'] + ":" + repository['file_path'] + "\n"
        table.add_row(rec['version'], JSON(json.dumps(rec['metadata'])), repo_string)

    console = Console()
    console.print(table)
    
@app.command(short_help='query packages, syntax: query-regex <ptype:npm/rust/golang/java/php/pip/ruby> <regex package_name>')
def query_regex(ptype: str, package_name: str):
    records = db.packages.find({"type": ptype, "name": {"$regex": package_name}})
    table = Table(title="Query result for package {}:{}".format(ptype, package_name),highlight=True)

    table.add_column("Version", justify="left", style="red", no_wrap=False)
    table.add_column("Metadata", justify="left", style="cyan")
    table.add_column("Repositories", style="magenta")
    for rec in records:
        repo_string = ""
        for repository in rec['repositories']:
            repo_string += repository['remote_path'] + "#" + repository['commit'] + ":" + repository['file_path'] + "\n"
        table.add_row(rec['name'] + "@" + rec['version'], JSON(json.dumps(rec['metadata'])), repo_string)

    console = Console()
    console.print(table)

@app.command(short_help='search repository, syntax: search-repository <regex:repository link>')
def search_repository(regex: str):
    records = db.repositories.find({"remote_path":{"$regex": regex}})
    table = Table(title="Query result for repository with the following pattern {}:".format(regex),highlight=True)

    table.add_column("Repository", justify="left", style="red", no_wrap=False)
    table.add_column("Commits", justify="left", style="cyan")
    res = {}
    for rec in records:
        if rec['remote_path'] in res:
            res[rec['remote_path']].append(rec['commit'] + ":" + rec['file_path'])
        else:
            res[rec['remote_path']] = [rec['commit']+ ":" + rec['file_path']]

    for remote_path, commits in res.items():
        table.add_row(remote_path, commits[0])
        for commit in commits[1:]:
            table.add_row("", commit)

    console = Console()
    console.print(table)

@app.command(short_help='query packages from a repository, syntax: query-repository <repository> <p_type:npm/rust/golang/java/php/pip/ruby(optional)')
def query_repository(repository: str, ptype: str = ""):
    if ptype != "":
        records = db.packages.find({"type": ptype, "repositories": { "$elemMatch": { "remote_path": repository}}})
    else:
        records = db.packages.find({"repositories.remote_path": repository})
    res = {}
    for rec in list(records):
        if rec['type'] in res:
            res[rec['type']].append(rec)
        else:
            res[rec['type']] = [rec]

    if len(res) == 0:
        print("[bold red]No packages found for [/bold red]{}".format(repository))
    else:
        for p_type, value in res.items():
            table = Table(title="Query result of [bold red]{}[/bold red] for repository [bold green]{}[/bold green]".format(p_type, repository),highlight=True)
        
            table.add_column("Name", justify="left", style="red", no_wrap=False)
            table.add_column("Version", justify="middle", style="red", no_wrap=False)
            table.add_column("Metadata", justify="left", style="cyan")
            for rec in value:
                table.add_row(rec['name'], rec['version'], JSON(json.dumps(rec['metadata'])))

            console = Console()
            console.print(table)
    
if __name__ == "__main__":
    app()