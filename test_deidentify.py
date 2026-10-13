"""Smoke test for the installed CLI module."""


def test_deidentify_import():
    from deidentify import main

    assert callable(main)
