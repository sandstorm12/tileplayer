import os

from shutil import copyfile


def copy_sample_config(destination_path):
    sample_config_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'config.yaml'
    )
    print(sample_config_path, destination_path)
    copyfile(sample_config_path, destination_path)