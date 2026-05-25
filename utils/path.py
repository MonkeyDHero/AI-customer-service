#为整个工程提供一个同一的绝对路径
import os

def get_project_root()->str:
    current_file=os.path.abspath(__file__)
    current_dir=os.path.dirname(current_file)
    project_dir=os.path.dirname(current_dir)
    return project_dir

def get_abs_path(relative_path)->str:
    project_root=get_project_root()
    return os.path.join(project_root,relative_path)