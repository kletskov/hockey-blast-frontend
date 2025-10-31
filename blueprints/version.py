import subprocess

import pkg_resources
from flask import Blueprint, render_template

version_bp = Blueprint("version", __name__)


def get_installed_version(library_name):
    try:
        return pkg_resources.get_distribution(library_name).version
    except pkg_resources.DistributionNotFound:
        return "Version not found"


@version_bp.route("/version")
def version():
    try:
        commit_message = (
            subprocess.check_output(["git", "log", "-1", "--pretty=%B"])
            .decode("utf-8")
            .strip()
        )
        commit_hash = (
            subprocess.check_output(["git", "rev-parse", "HEAD"])
            .decode("utf-8")
            .strip()
        )
        commit_date = (
            subprocess.check_output(["git", "log", "-1", "--format=%cd"])
            .decode("utf-8")
            .strip()
        )
    except subprocess.CalledProcessError:
        commit_message = "Error retrieving commit message"
        commit_hash = "Error retrieving commit hash"
        commit_date = "Error retrieving commit date"

    library_version = get_installed_version("hockey-blast-common-lib")

    return render_template(
        "version.html",
        commit_message=commit_message,
        commit_hash=commit_hash,
        commit_date=commit_date,
        library_version=library_version,
    )
