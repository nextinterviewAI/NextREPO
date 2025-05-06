#!/bin/bash

# Create a virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create deployment package directory
mkdir -p deployment_package

# Copy all Python files
cp *.py deployment_package/
cp -r routes deployment_package/
cp -r services deployment_package/

# Copy dependencies
cd venv/lib/python3.9/site-packages
zip -r ../../../../deployment_package/lambda_function.zip .
cd ../../../..

# Add your code to the zip
cd deployment_package
zip -g lambda_function.zip *.py
zip -r lambda_function.zip routes/
zip -r lambda_function.zip services/

echo "Deployment package created at deployment_package/lambda_function.zip" 