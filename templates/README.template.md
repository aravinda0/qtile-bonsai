<!-- 
README.md is a generated file! 

To make modifications, make sure you're editing `templates/README.template.md`.
Then generate the README with `python scripts/generate_readme.py`
-->


# Qtile Bonsai

[![CI Status](https://github.com/aravinda0/qtile-bonsai/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/aravinda0/qtile-bonsai/actions?query=branch%3Amaster)
[![codecov](https://codecov.io/gh/aravinda0/qtile-bonsai/branch/master/graph/badge.svg?token=O0PSWZMHM6)](https://codecov.io/gh/aravinda0/qtile-bonsai)
[![License - MIT](https://img.shields.io/github/license/qtile/qtile.svg)](https://github.com/aravinda0/qtile-bonsai/blob/master/LICENSE.txt)

-----

### :construction: :construction: This is a work in progress :construction: :construction:

<br/>


## Introduction

_Qtile Bonsai_ provides a flexible layout for the
[qtile](https://github.com/qtile/qtile) tiling window manager that allows you to
open windows as tabs, splits and even tabs inside splits.


## Reference

### Configuration

| Option Name | Default Value | Description |
| ---         | ---           | ---         |
{% for config_option in config_options %}|`{{ config_option.name }}` | {{ config_option.default }} | {{ config_option.description }} |
{% endfor %}


### Commands

| Command Name | Description |
| ---          | ---         |
{% for command in commands %}|`{{ command.name }}()` | {{ command.docstring }} |
{% endfor %}
