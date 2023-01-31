from setuptools import setup

setup(
    name='moneymaker',
    version='0.1',
    description='A sample Python package',
    author='James Williams',
    author_email='cfossguy@gmail.com',
    packages=['moneymaker'],
    include_package_data=True,
    install_requires=[
        'flask',
        'pandas',
        'Flask',
        'logfmter',
        'prometheus_flask_exporter',
        'python-dotenv',
        'SQLAlchemy',
        'polygon-api-client',
        'openpyxl',
        'psycopg2-binary'
    ],
)