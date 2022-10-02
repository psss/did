from setuptools import setup

setup(
    name='demo-plugins',
    version='0.0.1',
    py_modules=['discover', 'provision'],
    entry_points={
        'tmt.plugin': [
            'ProvisionExample = provision:ProvisionExample',
            'DiscoverExample = discover:DiscoverExample',
            ]
        }
    )
