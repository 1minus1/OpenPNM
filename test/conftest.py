import pytest
from os.path import join, dirname, realpath
from os import mkdir
from shutil import rmtree


@pytest.fixture(autouse=True)
def fixtures_directory(request):
    fixture_dir = join(dirname(realpath(__file__)), 'fixtures')
    request.function.__globals__['FIXTURE_DIR'] = fixture_dir


@pytest.fixture(autouse=True)
def temp_directory(request):
    temp_dir = join(dirname(realpath(__file__)), 'temp')
    mkdir(temp_dir)
    request.function.__globals__['TEMP_DIR'] = temp_dir

    def clean():
        rmtree(temp_dir)
    request.addfinalizer(clean)
