# Interface for [CPR Simulator](https://pypi.org/project/cpr-rsi/)

## Overview

[Click here](https://cpr.hec.ca/) to access the online application. It is built using a Python library named [Streamlit](https://streamlit.io/). NGINX is used to force HTTPS.

## Dependencies

Install the dependencies in ``requirements.txt`` using pip:

``pip install -r requirements.txt``

**Note:** Python >= 3.7. Set the python version in ``runtime.txt``.

## How to run

* To run locally: ``streamlit run app.py``
* To run online: Check ``Procfile``. It has commands for ``nginx`` and ``streamlit`` (with port no. and theme color set) written together. Heroku detects this file automatically.

## Streamlit API Reference

Streamlit is a Python library that turns your Python script into an interactive web app without having to know any web development framework.

* [Get started](https://docs.streamlit.io/en/stable/getting_started.html)
* [API reference](https://docs.streamlit.io/en/stable/api.html) for examples of every Streamlit command

## How to make changes

* Modify ``app_en.py`` and ``app_fr.py`` to update English and French version respectively; these files are called by ``app.py``.
* Test the changes locally (by running ``streamlit run app.py``)
* Change ``requirements.txt`` if new version of libraries are required (using >= or == for specific versions)
* Commit and push to automatically deploy to Heroku.
