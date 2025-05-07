# Clean up existing files
Remove-Item -Path "deployment_package" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "lambda_function.zip" -Force -ErrorAction SilentlyContinue

# Create deployment package directory
New-Item -ItemType Directory -Force -Path "deployment_package"

# Copy main application files
Copy-Item "main.py" -Destination "deployment_package/"
Copy-Item "lambda_handler.py" -Destination "deployment_package/"
Copy-Item "requirements.txt" -Destination "deployment_package/"

# Create directories
New-Item -ItemType Directory -Force -Path "deployment_package/services"
New-Item -ItemType Directory -Force -Path "deployment_package/routes"
New-Item -ItemType Directory -Force -Path "deployment_package/models"

# Copy service files
Copy-Item "services/*.py" -Destination "deployment_package/services/" -Recurse

# Copy route files
Copy-Item "routes/*.py" -Destination "deployment_package/routes/" -Recurse

# Copy model files
Copy-Item "models/*.py" -Destination "deployment_package/models/" -Recurse

# Install dependencies in the deployment package
Set-Location deployment_package

# Install all requirements
python -m pip install --upgrade --force-reinstall -r requirements.txt -t .

# Remove unnecessary files to reduce package size
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue *.dist-info
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue *.egg-info
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue __pycache__
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue tests
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue test
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue docs
Remove-Item -Recurse -Force -ErrorAction SilentlyContinue *.pyc

# Create zip file
Compress-Archive -Path * -DestinationPath "../lambda_function.zip" -Force

# Return to original directory
Set-Location ..

Write-Host "Deployment package created at lambda_function.zip" 