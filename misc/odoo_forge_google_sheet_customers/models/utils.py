import subprocess
import pkg_resources
import sys
import logging
from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

def install_package_if_not_installed(packages: dict):
    _logger.info("Starting install_package_if_not_installed...")
    python_version = f"python{sys.version_info.major}.{sys.version_info.minor}"
    for package in packages:
        try:
            _logger.warning(f"Checking if {package} is installed...")
            package_installed = pkg_resources.get_distribution(package)
            _logger.info(f"{package} is already installed. {package_installed}")
        except pkg_resources.DistributionNotFound:
            _logger.info(f"Installing {package}...")
            try:
                result = subprocess.run([sys.executable, "-m", "pip", "install", package], capture_output=True, text=True)
                _logger.warning(f"result: {result}")
                if result.returncode != 0:
                    _logger.error(f"Error installing package: {result.stderr}")
                    # raise UserError(_(f'Failed to activate module. Please install {package} manually.'))
            except subprocess.CalledProcessError as e:
                _logger.error(f"Failed to install {package}. Error: {e}")

packages = ['gspread','oauth2client','gspread_formatting']  
install_package_if_not_installed(packages)
