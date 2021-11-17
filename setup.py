from setuptools import setup, find_namespace_packages

setup(
    name='bristolhackspace.induction_site',
    packages=find_namespace_packages(include=['bristolhackspace.*']),
    package_data={
        "bristolhackspace": ["*"],
    },
    install_requires=[
        'bristolhackspace.flask_utils @ git+ssh://git@github.com/bristolhackspace/flask-utils.git@main'
    ],
)