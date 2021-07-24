import importlib


def test_imports():
    importlib.import_module("sphinxcontrib.hy_documenters")
    importlib.import_module("sphinxcontrib.hydomain")

    assert True
