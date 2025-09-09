#!/bin/bash

# Script to update hockey-blast-common-lib version in production requirements
# Usage: ./update-common-lib-version.sh 0.1.54

if [ $# -eq 0 ]; then
    echo "Usage: $0 <version>"
    echo "Example: $0 0.1.54"
    exit 1
fi

VERSION=$1

echo "Updating hockey-blast-common-lib to version $VERSION..."

# Update the version in requirements-prod.txt
sed -i '' "s/hockey-blast-common-lib==.*/hockey-blast-common-lib==$VERSION/" requirements-prod.txt

echo "Updated requirements-prod.txt with hockey-blast-common-lib==$VERSION"
echo "Remember to commit and push these changes for production deployment!"

# Show the change
echo ""
echo "Current production requirements:"
grep "hockey-blast-common-lib" requirements-prod.txt