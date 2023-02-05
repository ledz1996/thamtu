import json
import tempfile
import os

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
            'rust': []',
            'golang': []
        }
        
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
        return nil
    
    def get_file_list(self):
        return []
        
    def find_files(self):
        files = self.get_file_list()
        for type, glob in self.package_files:
            for pattern in glob:
                for file in files:
                    if fnmatch.fnmatch(file, pattern):
                        with tempfile.TemporaryDirectory() as tmp_dir:
                            f = open(tmp_dir + "/" + os.path.basename(file), "w")
                            f.write(get_file(file))
                            f.close()
                            output, error = self.run_syft(tmp_dir + "/" + os.path.basename(file), type)
         
    def get_file(path: str):
        return nil
        
    def run_syft(self, file_path: str, type: str):
        try:
            args = ["syft", file_path, "-o", "json"]
            output, error = subprocess.Popen(args,stdout = subprocess.PIPE, stderr= subprocess.PIPE).communicate()
            packages = json.loads(output)
            for package in packages['artifacts']:
                if package['metadata'] == None or len(package['metadata']) == 0:
                    package['metadata'] = {}
                package_object = {
                    'name': pacakge['name'],
                    'version': package['version'],
                    'metadata': package['metadata'],
                    'purl': package['purl']
                }
                self.loaded_packages[type].append(package_object)
            return 1, None
        except Exception as err:
            return -1, err
        
    def put_to_db(self, db):
        try:
            for type, packages in loaded_packages.items():
                for package in packages:
                    filter = {'purl': package['purl']}
                    if len(package['metadata'] !=0)):
                        for key, value in package['metadata']:
                            filter['metatdata.' + key] = value
                    else:
                        filter['metadata'] = {}
                    if db.packages.find_one_and_update(filter,{"$push":{"repositories":{"remote_path": self.remote_path, "commit": self.commit}}}) == None:
                        object_to_insert = package
                        object_to_insert['type'] = type
                        object_to_insert['repositories'] = [{"remote_path": self.remote_path, "commit": self.commit}]
                        db.packages.insert_one(object_to_insert)
            return 1
        except Exception as err:
            return -1, err
        
        