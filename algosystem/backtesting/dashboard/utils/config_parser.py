def validate_config(config):
    """
    Validate the dashboard configuration

    Parameters:
    -----------
    config : dict
        Dashboard configuration from graph_config.json

    Returns:
    --------
    bool
        True if configuration is valid

    Raises:
    -------
    ValueError
        If configuration is invalid
    """
    # Check for required sections
    required_sections = ["metrics", "charts", "layout"]
    for section in required_sections:
        if section not in config:
            raise ValueError(
                f"Missing required section '{section}' in dashboard configuration"
            )

    # Validate metrics
    validate_components(config["metrics"], "metrics")

    # Validate charts
    validate_components(config["charts"], "charts")

    # Validate layout
    validate_layout(config["layout"])

    return True


def validate_components(components, component_type):
    """
    Validate component configurations (metrics or charts)

    Parameters:
    -----------
    components : list
        List of component configurations
    component_type : str
        Type of components ('metrics' or 'charts')

    Raises:
    -------
    ValueError
        If configuration is invalid
    """
    if not isinstance(components, list):
        raise ValueError(f"'{component_type}' must be a list")

    # Check if list is empty
    if len(components) == 0:
        raise ValueError(f"No {component_type} specified in configuration")

    # Required fields for all components
    required_fields = ["id", "type", "title", "position"]

    # Additional required fields based on component type
    if component_type == "metrics":
        required_fields.append("value_key")
    elif component_type == "charts":
        required_fields.append("data_key")
        required_fields.append("config")

    # Check each component
    ids = set()
    for i, component in enumerate(components):
        # Check required fields
        for field in required_fields:
            if field not in component:
                raise ValueError(
                    f"Missing required field '{field}' in {component_type}[{i}]"
                )

        # Check for duplicate IDs
        if component["id"] in ids:
            raise ValueError(f"Duplicate ID '{component['id']}' in {component_type}")
        ids.add(component["id"])

        # Validate position
        validate_position(component["position"], f"{component_type}[{i}]")


def validate_position(position, context):
    """
    Validate component position configuration

    Parameters:
    -----------
    position : dict
        Position configuration
    context : str
        Context for error messages

    Raises:
    -------
    ValueError
        If position configuration is invalid
    """
    # Check required fields
    required_fields = ["row", "col"]
    for field in required_fields:
        if field not in position:
            raise ValueError(
                f"Missing required field '{field}' in position of {context}"
            )

    # Check that row and col are non-negative integers
    if not isinstance(position["row"], int) or position["row"] < 0:
        raise ValueError(
            f"'row' must be a non-negative integer in position of {context}"
        )

    if not isinstance(position["col"], int) or position["col"] < 0:
        raise ValueError(
            f"'col' must be a non-negative integer in position of {context}"
        )


def validate_layout(layout):
    """
    Validate layout configuration

    Parameters:
    -----------
    layout : dict
        Layout configuration

    Raises:
    -------
    ValueError
        If layout configuration is invalid
    """
    # Check required fields
    required_fields = ["max_cols", "title"]
    for field in required_fields:
        if field not in layout:
            raise ValueError(f"Missing required field '{field}' in layout")

    # Check that max_cols is a positive integer
    if not isinstance(layout["max_cols"], int) or layout["max_cols"] <= 0:
        raise ValueError("'max_cols' must be a positive integer in layout")

    # Check that title is a string
    if not isinstance(layout["title"], str):
        raise ValueError("'title' must be a string in layout")


def get_component_rows(components):
    """
    Group components by row

    Parameters:
    -----------
    components : list
        List of component configurations

    Returns:
    --------
    dict
        Dictionary with rows as keys and lists of components as values
    """
    rows = {}
    for component in components:
        row = component["position"]["row"]
        if row not in rows:
            rows[row] = []
        rows[row].append(component)

    # Sort components within each row by column
    for row in rows:
        rows[row].sort(key=lambda x: x["position"]["col"])

    return rows


def get_max_row(config):
    """
    Get the maximum row number used in the configuration

    Parameters:
    -----------
    config : dict
        Dashboard configuration

    Returns:
    --------
    int
        Maximum row number
    """
    max_row = 0

    # Check metrics
    for metric in config["metrics"]:
        max_row = max(max_row, metric["position"]["row"])

    # Check charts
    for chart in config["charts"]:
        max_row = max(max_row, chart["position"]["row"])

    return max_row
