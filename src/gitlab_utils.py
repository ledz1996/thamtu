from base_util import BaseUtil

class GitLabUtil(BaseUtil):
    
    def __init__(self, remote_path, commit, project):
        super().__init__(remote_path, commit)
        self.project = project
        self.prefix = "./"
    
    def get_repository(self):
        self.remote_path = self.project.web_url
        self.commit = self.project.commits.list(ref_name=self.project.default_branch)[0].id
    
    def get_file_list(self):
        return ["./" + x['path'] for x in self.project.repository_tree(all=True, recursive=True) if x['type'] == "blob"]
        
    def get_file(self, path: str):
        return self.project.files.raw(file_path=path[2:], ref=self.project.default_branch)
        
        