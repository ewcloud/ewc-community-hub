#!/bin/bash

# NOTE TO DEVS:
# This scripts ensures a consistent coding style is used. 
# Make sure to run it before committing code changes.

black --line-length 120 ./
flake8 ./
mypy --show-error-codes --pretty ./