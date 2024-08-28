# Development & Packaging

MQTTBuzz is written in Python and uses rumps and py2app to provide the OSX interface

## The application files

These are the core files and their purpose

 * src/MQTTBuzz.py - the python script that does the work
 * src/config.json - the configuration file
 * src/help.txt - the help file
 * setup.py - used by py2app to build the application
 * MQTTBuzz.icns - icons used for the application in Apple .icns format

## Set up the development environment

We recommend working in a Python virtual environment (see https://docs.python.org/3/library/venv.html) as follows:

First open a terminal/shell session and then

```
# Get the source code from GitHub
git clone https://github.com/datamgmt/MQTTBuzz

# Create a virtual environment
python -m venv MQTTBuzz

# Activate the virtual environment 
source MQTTBuzz/bin/activate

# Change Directory
cd MQTTBuzz

# Make sure the environment is up to date
pip install --upgrade pip

# Install and/or upgrade the required libraries
pip install --upgrade paho-mqtt py2app rumps

# Install a specific version of setuptools to overcome a bug in the current release
pip install setuptools==70.3.0
```

## Running the application

Running the application is simple

```
# Change directory into the source directory
cd src

# Run the application
python ./MQTTBuzz.py
```

You can then make any changes required to python code

## Build and package the application

Building the application is simple
First go to the root directory of MQTTBuzz
One there 

```
# Build the application
python setup.py py2app

# Copy the application to the application directory (optional)
cp dist/MQTTBuzz.app /Applications
```

This message can be safely ignored:
```
!!

        ********************************************************************************
        Requirements should be satisfied by a PEP 517 installer.
        If you are using pip, you can try `pip install --use-pep517`.
        ********************************************************************************

!!
```
