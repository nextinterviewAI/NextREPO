# Clean up existing files
Remove-Item -Path "deployment_package" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path "lambda_function.zip" -Force -ErrorAction SilentlyContinue

# Create deployment package directory
New-Item -ItemType Directory -Force -Path "deployment_package"

# Copy main application files
Copy-Item "main.py" -Destination "deployment_package/"
Copy-Item "lambda_handler.py" -Destination "deployment_package/"

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

# Create and activate virtual environment
python -m venv venv-lambda
.\venv-lambda\Scripts\Activate.ps1

# Install dependencies in the deployment package
Set-Location deployment_package

# Install all requirements
python -m pip install --upgrade pip
python -m pip install -r ../requirements.txt -t .

# Remove unnecessary files to reduce package size
Get-ChildItem -Recurse -Include *.dist-info,*.egg-info,__pycache__,tests,test,docs,*.pyc,*.pyo | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Optionally remove sounddevice if not needed (uncomment if not required)
# Remove-Item -Recurse -Force -ErrorAction SilentlyContinue sounddevice*

# Create zip file
Compress-Archive -Path * -DestinationPath "../lambda_function.zip" -Force

# Return to original directory
Set-Location ..

# Clean up
deactivate
Remove-Item -Recurse -Force venv-lambda

Write-Host "Deployment package created at lambda_function.zip" 