# Hockey Blast Development Setup

Follow these steps to set up the development environment for the Hockey Blast project.

## Initial Setup

1. Create a new directory and navigate into it:
    ```bash
    mkdir hockey-blast
    cd hockey-blast
    ```

2. Initialize a new Git repository:
    ```bash
    git init
    ```

3. Clone the necessary repositories:
    ```bash
    git clone https://github.com/kletskov/hockey-blast-frontend.git 
    git clone https://github.com/kletskov/hockey-blast-common-lib.git
    ```

## Python Environment Setup

1. Create a virtual environment:
    ```bash
    python3 -m venv .venv
    ```

2. Activate the virtual environment:
    ```bash
    source .venv/bin/activate
    ```

3. Install the required Python packages:
    ```bash
    pip install -r hockey-blast-frontend/requirements.txt
    ```

## PostgreSQL Setup

### Install Homebrew

1. Install Homebrew by running the following command in your terminal:
    ```bash
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    ```

2. Follow the on-screen instructions. Once the installation is complete, ensure that Homebrew is added to your PATH by adding the following line to your shell configuration file (e.g., `.zshrc` for zsh):
    ```bash
    export PATH="/usr/local/bin:/usr/local/sbin:$PATH"
    ```

### Install PostgreSQL

1. Install PostgreSQL using Homebrew:
    ```bash
    brew install postgresql
    ```

2. Initialize the database:
    ```bash
    initdb /opt/homebrew/var/postgresql
    ```

3. Start the PostgreSQL service:
    ```bash
    pg_ctl -D ./postgres_data start
    brew services start postgresql
    ```

4. Create roles in PostgreSQL:
    ```bash
    psql postgres
    postgres=# CREATE ROLE your_superuser WITH SUPERUSER LOGIN PASSWORD 'your_superuser_password';
    postgres=# CREATE ROLE boss WITH SUPERUSER LOGIN PASSWORD 'boss';
    ```

## Restore Sample Database

1. Navigate to the common library directory:
    ```bash
    cd hockey-blast-common-lib/hockey_blast_common_lib
    ```

2. Run the script to restore the sample database:
    ```bash
    ./restore_sample_db.sh
    ```

## Running the Application

1. Modify the `flask_table` files to fix the import error:
    - Edit the following files:
        - `.venv/lib/python3.9/site-packages/flask_table/html.py`
        - `.venv/lib/python3.9/site-packages/flask_table/columns.py`
        - `.venv/lib/python3.9/site-packages/flask_table/table.py`
    - Change the import statement from:
        ```python
        # from flask import Markup
        from markupsafe import Markup
        ```

2. Start the application:
    ```bash
    python hockey-blast-frontend/app.py
    ```

3. If you encounter an "Address already in use" error, try disabling the 'AirPlay Receiver' service from System Preferences -> General -> AirDrop & Handoff.

4. Open the application in your browser:
    ```
    http://localhost:5005/
    ```
