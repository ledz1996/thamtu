from base_util import BaseUtil
import git
import os

class GitUtil(BaseUtil):
    
    def __init__(self, remote_path, commit, git_repo, local_path):
        super().__init__(self, remote_path, commit)
        self.git_repo = git_repo
        self.local_path = local_path
        
    def get_repository(self):
        self.commit = self.git_repo.head.commit.hexsha
    
    def get_file_list(self):
        files = []
        return glob.iglob(self.local_path + '/**/*', recursive=True)
        
    def get_file(path: str):
        f = open(path)
        s = f.read()
        f.close()
        return s        
        