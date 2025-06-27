#!/bin/bash

# Locate the install path dynamically
SITE_PACKAGES=$(python -c "import site; print(site.getsitepackages()[0])")
FLASK_TABLE_DIR="$SITE_PACKAGES/flask_table"

# Patch flask_table to use Markup from markupsafe
sed -i 's/from flask import Markup, url_for/from markupsafe import Markup\nfrom flask import url_for/' "$FLASK_TABLE_DIR/columns.py"
sed -i 's/from flask import Markup/from markupsafe import Markup/' "$FLASK_TABLE_DIR/html.py"
sed -i 's/from flask import Markup/from markupsafe import Markup/' "$FLASK_TABLE_DIR/table.py"
