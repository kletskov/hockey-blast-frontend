#!/bin/bash

# Patch flask_table to use Markup from markupsafe
sed -i 's/from flask import Markup, url_for/from markupsafe import Markup\nfrom flask import url_for/' /usr/local/lib/python3.9/site-packages/flask_table/columns.py
sed -i 's/from flask import Markup/from markupsafe import Markup/' /usr/local/lib/python3.9/site-packages/flask_table/html.py
sed -i 's/from flask import Markup/from markupsafe import Markup/' /usr/local/lib/python3.9/site-packages/flask_table/table.py