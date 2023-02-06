import json
import tempfile
import os
import fnmatch
import subprocess
import traceback

class BaseUtil:
    def __init__(self, remote_path, commit):
        self.remote_path = remote_path
        self.list_files = []
        self.commit = ""
        self.loaded_packages = {
            'npm': [],
            'php': [],
            'java': [],
            'pip': [],
            'ruby': [],
            'conan': [],
            'rust': [],
            'golang': []
        }
        self.prefix = ""
        
    package_files = {
        'npm': ["**/package-lock.json","**/yarn.lock","**/pnpm-lock.yaml","**/packages.json"],
        'php': ["**/installed.json","**/composer.lock"],
        'java': ["**/*.jar","**/*.war","**/*.ear","**/*.par","**/*.sar","**/*.jpi","**/*.hpi","**/*.lpkg"],
        'pip': ["**/*requirements*.txt","**/poetry.lock","**/Pipfile.lock","**/setup.py","**/*egg-info/PKG-INFO","**/*.egg-info","**/*dist-info/METADATA"],
        'ruby': ['**/Gemfile.lock',],
        'conan': ["**/conanfile.txt","**/conan.lock"],
        'rust': ['**/Cargo.lock'],
        'golang': ['**/go.mod']
    }
    
    def get_repository(self):
        return None
    
    def get_file_list(self):
        return []
        
    def find_files(self):
        files = self.get_file_list()
        for p_type, glob in self.package_files.items():
            for pattern in glob:
                for file in files:
                    if fnmatch.fnmatch(file, pattern):
                        with tempfile.TemporaryDirectory() as tmp_dir:
                            f = open(tmp_dir + "/" + os.path.basename(file), "wb")
                            f.write(self.get_file(file))
                            f.close()
                            output, error = self.run_syft(tmp_dir + "/" + os.path.basename(file), p_type, file)
         
    def get_file(self, path: str):
        return None
        
    def run_syft(self, file_path: str, type: str, true_path: str):
        try:
            args = ["syft", file_path, "-o", "json"]
            output, error = subprocess.Popen(args,stdout = subprocess.PIPE, stderr= subprocess.PIPE).communicate()
            packages = json.loads(output)
            for package in packages['artifacts']:
                if 'metadata' not in package:
                    package['metadata'] = {}
                package_object = {
                    'name': package['name'],
                    'version': package['version'],
                    'metadata': package['metadata'],
                    'purl': package['purl'],
                    'file_path': true_path[len(self.prefix):]
                }
                self.loaded_packages[type].append(package_object)
            return 1, None
        except Exception as err:
            print (str(err))
            traceback.print_exc()
            return -1, err
        
    def put_to_db(self, db):
        try:
            for p_type, packages in self.loaded_packages.items():
                for package in packages:
                    filter = {'purl': package['purl']}
                    if len(package['metadata']) != 0:
                        for key, value in package['metadata'].items():
                            filter['metadata.' + key] = value
                    else:
                        filter['metadata'] = {}
                    found_package = db['packages'].find_one(filter)
                    if found_package == None:
                        file_path = package['file_path']
                        del package['file_path']
                        object_to_insert = package
                        object_to_insert['type'] = p_type
                        object_to_insert['repositories'] = [{"remote_path": self.remote_path, "commit": self.commit, "file_path": file_path}]
                        db['packages'].insert_one(object_to_insert)
                    else:
                        file_path = package['file_path']
                        list_of_repos = found_package['repositories']
                        list_of_repos.append({"remote_path": self.remote_path, "commit": self.commit, "file_path": file_path})
                        list_of_repos = [dict(s) for s in set(frozenset(d.items()) for d in list_of_repos)]
                        db['packages'].update_one({"_id": found_package['_id']}, {"$set": {"repositories": list_of_repos}})
            db['repositories'].insert_one({"remote_path": self.remote_path, "commit": self.commit})   
            return 1, None
        except Exception as err:
            print (str(err))
            traceback.print_exc()
            return -1, err
        
        