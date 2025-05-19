import json
import logging
import os

import pandas as pd
from flask import (
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

from algosystem.backtesting.engine import Engine

# Set up logging
logger = logging.getLogger(__name__)

# Import available components
from algosystem.backtesting.dashboard.web_app.available_components import (
    AVAILABLE_CHARTS,
    AVAILABLE_METRICS,
)

# Global references that will be set when routes are registered
uploaded_data = None
engine = None
dashboard_path = None


def register_routes(
    app,
    load_config_func,
    save_config_func,
    default_config_path,
    config_path,
    save_config_path,
):
    """
    Register all routes for the Flask application.

    Parameters:
    -----------
    app : Flask
        Flask application
    load_config_func : function
        Function to load configuration
    save_config_func : function
        Function to save configuration
    default_config_path : str
        Path to default configuration
    config_path : str
        Path to current configuration
    save_config_path : str
        Path where to save configuration
    """
    global uploaded_data, engine, dashboard_path

    @app.route("/")
    def index():
        """Render the dashboard editor."""
        config = load_config_func()
        logger.info(f"Rendering index with configuration loaded from: {config_path}")
        return render_template(
            "index.html",
            config=config,
            available_charts=AVAILABLE_CHARTS,
            available_metrics=AVAILABLE_METRICS,
            data_loaded=(uploaded_data is not None),
        )

    @app.route("/api/config", methods=["GET"])
    def get_config():
        """Get the current configuration."""
        config = load_config_func()
        logger.info("Retrieved configuration for API request")
        return jsonify(config)

    @app.route("/api/config", methods=["POST"])
    def update_config():
        """Update the configuration."""
        try:
            # Get the JSON data from the request
            config_data = request.get_json()

            if not config_data:
                logger.error("Received empty or invalid configuration data")
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": "Empty or invalid configuration data",
                        }
                    ),
                    400,
                )

            # Log the configuration size
            metrics_count = len(config_data.get("metrics", []))
            charts_count = len(config_data.get("charts", []))
            logger.info(
                f"Received configuration update with {metrics_count} metrics and {charts_count} charts"
            )
            print(
                f"Received configuration update with {metrics_count} metrics and {charts_count} charts"
            )

            # Validate minimal configuration structure
            if (
                not isinstance(config_data, dict)
                or "metrics" not in config_data
                or "charts" not in config_data
                or "layout" not in config_data
            ):
                logger.warning("Configuration missing required sections")
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": "Configuration missing required sections (metrics, charts, or layout)",
                        }
                    ),
                    400,
                )

            # Determine save path
            save_path = save_config_path if save_config_path else config_path

            # Write the configuration to a temporary file first (for debug purposes)
            debug_path = os.path.join(os.path.dirname(save_path), "debug_config.json")
            try:
                with open(debug_path, "w") as f:
                    json.dump(config_data, f, indent=4)
                print(f"Debug configuration saved to: {debug_path}")
            except Exception as debug_error:
                print(f"Could not save debug config: {str(debug_error)}")

            # Save the configuration
            from algosystem.backtesting.dashboard.web_app.app import save_config

            success = save_config(config_data, save_path)

            if success:
                logger.info(f"Configuration successfully saved to {save_path}")
                return jsonify(
                    {
                        "status": "success",
                        "message": "Configuration saved successfully",
                        "path": save_path,
                    }
                )
            else:
                logger.error(f"Failed to save configuration to {save_path}")
                return jsonify(
                    {"status": "error", "message": "Failed to save configuration"}
                ), 500

        except Exception as e:
            logger.exception(f"Error updating configuration: {str(e)}")
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"Error updating configuration: {str(e)}",
                    }
                ),
                500,
            )

    @app.route("/api/config/save-location", methods=["GET"])
    def get_config_save_location():
        """Get the location where the configuration will be saved."""
        save_path = save_config_path if save_config_path else config_path
        return jsonify({"save_path": save_path})

    @app.route("/api/reset-config", methods=["POST"])
    def reset_config():
        """Reset to the default configuration."""
        try:
            # Load default config
            with open(default_config_path, "r") as f:
                default_config = json.load(f)
            logger.info(f"Loaded default configuration from {default_config_path}")

            # Save to the current config path (don't modify the default config file)
            success = save_config_func(default_config, save_config_path)

            if success:
                logger.info("Reset configuration successfully to default")
                return jsonify(
                    {
                        "status": "success",
                        "message": "Reset to default configuration successfully",
                    }
                )
            else:
                logger.error("Failed to reset configuration")
                return jsonify(
                    {"status": "error", "message": "Failed to reset configuration"}
                ), 500
        except Exception as e:
            logger.exception(f"Error resetting configuration: {str(e)}")
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": f"Error resetting configuration: {str(e)}",
                    }
                ),
                500,
            )

    @app.route("/dashboard")
    def view_dashboard():
        """View the generated dashboard."""
        if dashboard_path:
            dashboard_dir = os.path.dirname(dashboard_path)
            logger.info(f"Serving dashboard from {dashboard_dir}")
            return send_from_directory(dashboard_dir, "dashboard.html")
        else:
            logger.warning("No dashboard available, redirecting to index")
            return redirect(url_for("index"))

    @app.route("/dashboard/<path:filename>")
    def dashboard_files(filename):
        """Serve dashboard files."""
        if dashboard_path:
            dashboard_dir = os.path.dirname(dashboard_path)
            logger.info(f"Serving dashboard file: {filename}")
            return send_from_directory(dashboard_dir, filename)
        else:
            logger.warning("No dashboard available, redirecting to index")
            return redirect(url_for("index"))

    @app.route("/api/upload-csv", methods=["POST"])
    def upload_csv():
        """Upload and process a CSV file."""
        global uploaded_data, engine, dashboard_path

        if "file" not in request.files:
            logger.warning("No file part in the request")
            return jsonify(
                {"status": "error", "message": "No file part in the request"}
            )

        file = request.files["file"]

        if file.filename == "":
            logger.warning("No file selected")
            return jsonify({"status": "error", "message": "No file selected"})

        if file and file.filename.endswith(".csv"):
            # Create upload folder if it doesn't exist
            upload_folder = app.config["UPLOAD_FOLDER"]
            os.makedirs(upload_folder, exist_ok=True)

            # Save the file temporarily
            filename = secure_filename(file.filename)
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)
            logger.info(f"Saved uploaded file to {filepath}")

            try:
                # Process the CSV file
                data = pd.read_csv(filepath, index_col=0, parse_dates=True)
                logger.info(f"Processed CSV file with shape {data.shape}")

                # Create a backtest engine
                engine = Engine(data=data)
                results = engine.run()
                logger.info(f"Ran backtest with result keys: {list(results.keys())}")

                # Generate dashboard
                current_config = load_config_func()
                dashboard_path = engine.generate_dashboard(
                    output_dir=upload_folder,
                    open_browser=False,
                    config_path=None,  # Use the config we loaded
                )
                logger.info(f"Generated dashboard at {dashboard_path}")

                # Store the data for later use
                uploaded_data = data

                return jsonify(
                    {
                        "status": "success",
                        "message": f"File {file.filename} uploaded and processed successfully.",
                        "dashboard_path": dashboard_path,
                    }
                )
            except Exception as e:
                logger.exception(f"Error processing CSV: {str(e)}")
                return jsonify(
                    {"status": "error", "message": f"Error processing file: {str(e)}"}
                )
        else:
            logger.warning(f"Invalid file format: {file.filename}")
            return jsonify(
                {
                    "status": "error",
                    "message": "Invalid file format. Please upload a CSV file.",
                }
            )

    # Return references to the global variables
    return {
        "uploaded_data": uploaded_data,
        "engine": engine,
        "dashboard_path": dashboard_path,
    }
