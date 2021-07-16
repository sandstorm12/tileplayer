from setuptools import setup


def read_requirements(path='./requirements.txt'):
    with open(path, encoding='utf-8', errors='ignore') as file:
        install_requires = file.readlines()

    return install_requires


setup(
    name="TilePlayer",
    version="1.0.0",
    author="Hamid Mohammadi",
    author_email="sandstormeatwo@gmail.com",
    description="Multi-stream tile player based on gstreamer",
    packages=['tile_player'],
    scripts=[
        'tileplayer'
    ],
    include_package_data=True,
    install_requires=read_requirements()
)
