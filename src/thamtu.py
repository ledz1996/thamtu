import typer
from git_utils import GitUtil
from gitlab_utils import GitLabUtil
import urlparse
from rich.console import Console
from rich.table import Table
from rich.json import JSON
import tempfile
import os
import json

app = typer.Typer()
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
                authSource='the_database',
                authMechanism='SCRAM-SHA-256')[mongo_db]

@app.command(short_help='analyze a git repository')
def add_git(remote_path: str):
    typer.echo(f"Analyzing git repo {remote_path}")
    with tempfile.TemporaryDirectory() as tmp_dir:
        git_repo = Repo.clone_from(remote_path, tmp_dir)
        git_analyzed_repo = GitUtil(remote_path, "", git_repo, tmp_dir)
        git_analyzed_repo.get_repository()
        git_analyzed_repo.find_files()
        git_analyzed_repo.put_to_db(db)
        
@app.command(short_help='analyze a gitlab repository')
def add_gitlab(remote_path: str):
    typer.echo(f"Analyzing GitLab repo {remote_path}")
    path = urlparse.urlparse(remote_path).path
    try:
        gitlab_repo = gl.projects.get(path[1:])
        gitlab_analyzed_repo = GitLabUtil(remote_path, "", gitlab_repo)
        gitlab_analyzed_repo.get_repository()
        gitlab_analyzed_repo.find_files()
        gitlab_analyzed_repo.put_to_db(db)
    except:
        typer.echo(f"Error fetching GitLab repo {remote_path}")

@app.command(short_help='analyze all visible gitlab repository')
def add_gitlab_all():
    typer.echo(f"Analyzing all visible GitLab repo")
    all_projects = gl.projects.list(all=True)
    with alive_bar(len(all_projects), ctrl_c=False, title=f'Analyzing {len(all_projects)} projects') as bar:
        for project in all_projects:
            if db.repositories.find_one({"remote_path": project.web_url, "commit": self.project.commits.list(ref_name=self.project.default_branch)[0].sha}) == None:
                gitlab_analyzed_repo = GitLabUtil(project.web_url, "", project)
                gitlab_analyzed_repo.get_repository()
                gitlab_analyzed_repo.find_files()
                gitlab_analyzed_repo.put_to_db(db)
            bar()
    

@app.command(short_help='query packages, syntax: query <type:npm/rust/golang/java/php/pip/ruby> <package_name>')
def query(type: str, package_name: str):
    records = db.packages.find({"type": type, "name": package_name})
    table = Table(title="Query result for package {}:{}".format(type, package_name),highlight=True)

    table.add_column("Version", justify="right", style="red", no_wrap=True)
    table.add_column("Metadata", justify="right", style="cyan")
    table.add_column("Repositories", style="magenta")
    for rec in records:
        repo_string = ""
        for repository in rec['repositories']:
            repo_string += repository['remote_path'] + "#" + repository['commit'] + "\n"
        table.add_row(rec['version'], json.dumps(rec['metadata']), repo_string)

    console = Console()
    console.print(table)
    
if __name__ == "__main__":
    app()