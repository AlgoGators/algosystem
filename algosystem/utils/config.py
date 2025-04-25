import sys, json, os
import numpy as np
from json import JSONDecodeError
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                           QWidget, QPushButton, QLabel, QMenu, QDialog, 
                           QGridLayout, QComboBox, QColorDialog, QSlider, QSpinBox,
                           QDoubleSpinBox, QCheckBox, QGroupBox, QToolButton, QScrollArea)
from PyQt6.QtCore import pyqtSignal, QPoint
import pyqtgraph as pg

# For saving and loading configurations
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "graph_config.json")

def load_config():
    default = {"graphs": []}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            try:
                return json.load(f)
            except JSONDecodeError:
                save_config(default)
                return default
    else:
        # Default configuration with no graphs
        save_config(default)
        return default

def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)

class GraphModule(QWidget):
    """A modular graph widget that can be customized and placed in the grid"""
    removed = pyqtSignal(object)  # Signal emitted when graph is removed
    
    def __init__(self, parent=None, graph_id=None, graph_type="line", title="Graph", config=None):
        super().__init__(parent)
        self.graph_id = graph_id if graph_id else id(self)  # Unique identifier
        self.graph_type = graph_type
        self.graph_title = title
        self.config = config or {}
        
        # Set up the layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(2, 2, 2, 2)
        
        # Header with title and controls
        header = QHBoxLayout()
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-weight: bold;")
        header.addWidget(self.title_label)
        
        # Spacer to push buttons to the right
        header.addStretch()
        
        # Settings button
        self.settings_btn = QToolButton()
        self.settings_btn.setText("⚙")
        self.settings_btn.clicked.connect(self.show_settings)
        header.addWidget(self.settings_btn)
        
        # Remove button
        self.remove_btn = QToolButton()
        self.remove_btn.setText("✕")
        self.remove_btn.clicked.connect(self.remove_self)
        header.addWidget(self.remove_btn)
        
        self.layout.addLayout(header)
        
        # The actual plot widget
        self.plot = pg.PlotWidget()
        self.plot.setTitle(title)
        self.plot.setBackground('w')
        self.plot.showGrid(x=True, y=True)
        self.layout.addWidget(self.plot)
        
        # Apply saved configuration if available
        self.apply_config()
        
        # Generate initial data
        self.generate_data()
        
    def apply_config(self):
        """Apply saved configuration to the graph"""
        if not self.config:
            return
            
        # Apply graph-specific settings
        if "title" in self.config:
            self.graph_title = self.config["title"]
            self.title_label.setText(self.graph_title)
            self.plot.setTitle(self.graph_title)
            
        if "background_color" in self.config:
            self.plot.setBackground(self.config["background_color"])
            
        if "grid" in self.config:
            self.plot.showGrid(x=self.config["grid"].get("x", True), 
                              y=self.config["grid"].get("y", True))
    
    def generate_data(self):
        """Generate sample data based on graph type"""
        self.plot.clear()
        
        if self.graph_type == "line":
            # Generate sample line data
            x = np.linspace(0, 10, 100)
            y = np.sin(x)
            self.plot.plot(x, y, pen=pg.mkPen(color='b', width=2))
            
        elif self.graph_type == "scatter":
            # Generate sample scatter data
            x = np.random.normal(size=100)
            y = np.random.normal(size=100)
            scatter = pg.ScatterPlotItem(x=x, y=y, size=10, pen=pg.mkPen(None), brush=pg.mkBrush(0, 0, 255, 120))
            self.plot.addItem(scatter)
            
        elif self.graph_type == "bar":
            # Generate sample bar data
            x = np.arange(10)
            y = np.random.randint(1, 10, size=10)
            bar_graph = pg.BarGraphItem(x=x, height=y, width=0.6, brush='g')
            self.plot.addItem(bar_graph)
    
    def show_settings(self):
        """Open settings dialog for this graph"""
        settings_dialog = GraphSettingsDialog(self, self.config)
        if settings_dialog.exec():
            # Update configuration based on dialog results
            self.config = settings_dialog.get_config()
            self.apply_config()
            self.generate_data()  # Re-generate data with new settings
    
    def remove_self(self):
        """Remove this graph from the parent layout"""
        self.removed.emit(self)
        self.deleteLater()
    
    def get_config_dict(self):
        """Return a dictionary with configuration for saving"""
        return {
            "id": self.graph_id,
            "type": self.graph_type,
            "title": self.graph_title,
            "config": self.config
        }

class GraphSettingsDialog(QDialog):
    """Dialog for editing graph settings"""
    
    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self.config = config or {}
        self.setWindowTitle("Graph Settings")
        self.setMinimumWidth(300)
        
        layout = QVBoxLayout(self)
        
        # Title settings
        title_group = QGroupBox("Title")
        title_layout = QHBoxLayout()
        title_group.setLayout(title_layout)
        
        self.title_edit = QComboBox()
        self.title_edit.setEditable(True)
        self.title_edit.addItems(["Temperature", "Pressure", "Voltage", "Current", "Custom Graph"])
        if "title" in self.config:
            self.title_edit.setCurrentText(self.config["title"])
        title_layout.addWidget(self.title_edit)
        
        layout.addWidget(title_group)
        
        # Visual settings
        visual_group = QGroupBox("Visual Settings")
        visual_layout = QGridLayout()
        visual_group.setLayout(visual_layout)
        
        # Background color
        visual_layout.addWidget(QLabel("Background:"), 0, 0)
        self.bg_color_btn = QPushButton()
        self.bg_color = self.config.get("background_color", "w")
        self.bg_color_btn.setStyleSheet(f"background-color: {self.bg_color}")
        self.bg_color_btn.clicked.connect(self.choose_bg_color)
        visual_layout.addWidget(self.bg_color_btn, 0, 1)
        
        # Grid options
        visual_layout.addWidget(QLabel("Show Grid:"), 1, 0)
        grid_layout = QHBoxLayout()
        
        self.grid_x = QCheckBox("X")
        self.grid_y = QCheckBox("Y")
        
        grid_config = self.config.get("grid", {"x": True, "y": True})
        self.grid_x.setChecked(grid_config.get("x", True))
        self.grid_y.setChecked(grid_config.get("y", True))
        
        grid_layout.addWidget(self.grid_x)
        grid_layout.addWidget(self.grid_y)
        visual_layout.addLayout(grid_layout, 1, 1)
        
        layout.addWidget(visual_group)
        
        # Data settings
        data_group = QGroupBox("Data Settings")
        data_layout = QGridLayout()
        data_group.setLayout(data_layout)
        
        # Sample rate
        data_layout.addWidget(QLabel("Sample Rate:"), 0, 0)
        self.sample_rate = QSpinBox()
        self.sample_rate.setRange(10, 1000)
        self.sample_rate.setValue(self.config.get("sample_rate", 100))
        data_layout.addWidget(self.sample_rate, 0, 1)
        
        layout.addWidget(data_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(self.accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(ok_button)
        layout.addLayout(button_layout)
    
    def choose_bg_color(self):
        """Open color picker for background color"""
        color = QColorDialog.getColor()
        if color.isValid():
            self.bg_color = color.name()
            self.bg_color_btn.setStyleSheet(f"background-color: {self.bg_color}")
    
    def get_config(self):
        """Return the updated configuration"""
        return {
            "title": self.title_edit.currentText(),
            "background_color": self.bg_color,
            "grid": {
                "x": self.grid_x.isChecked(),
                "y": self.grid_y.isChecked()
            },
            "sample_rate": self.sample_rate.value()
        }

class GraphDashboard(QMainWindow):
    """Main window containing the graph modules in a grid layout"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Graph Dashboard")
        self.resize(800, 600)
        
        # Main widget and layout
        self.central_widget = QWidget()
        self.main_layout = QVBoxLayout(self.central_widget)
        self.setCentralWidget(self.central_widget)
        
        # Toolbar for adding new graphs
        toolbar_layout = QHBoxLayout()
        self.add_graph_btn = QPushButton("Add Graph")
        self.add_graph_btn.clicked.connect(self.show_add_graph_menu)
        toolbar_layout.addWidget(self.add_graph_btn)
        
        toolbar_layout.addStretch()
        
        self.save_btn = QPushButton("Save Layout")
        self.save_btn.clicked.connect(self.save_dashboard)
        toolbar_layout.addWidget(self.save_btn)
        
        self.main_layout.addLayout(toolbar_layout)
        
        # Create a scroll area for the graph grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.grid_layout = QGridLayout(self.scroll_content)
        self.grid_layout.setSpacing(10)
        self.scroll_area.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll_area)
        
        # Track graph modules
        self.graphs = []
        self.current_row = 0
        self.current_col = 0
        self.max_cols = 2
        
        # Load saved configuration
        self.config = load_config()
        self.load_dashboard()
    
    def show_add_graph_menu(self):
        """Show menu with graph type options"""
        menu = QMenu(self)
        menu.addAction("Line Graph", lambda: self.add_graph("line"))
        menu.addAction("Scatter Plot", lambda: self.add_graph("scatter"))
        menu.addAction("Bar Graph", lambda: self.add_graph("bar"))
        menu.exec(self.add_graph_btn.mapToGlobal(QPoint(0, self.add_graph_btn.height())))
    
    def add_graph(self, graph_type):
        """Add a new graph module to the grid"""
        title = f"{graph_type.capitalize()} Graph {len(self.graphs) + 1}"
        graph = GraphModule(graph_type=graph_type, title=title)
        graph.removed.connect(self.remove_graph)
        
        # Add to grid layout
        self.grid_layout.addWidget(graph, self.current_row, self.current_col)
        
        # Update grid position for next graph
        self.current_col += 1
        if self.current_col >= self.max_cols:
            self.current_col = 0
            self.current_row += 1
        
        self.graphs.append(graph)
    
    def remove_graph(self, graph):
        """Remove a graph from tracking"""
        if graph in self.graphs:
            self.graphs.remove(graph)
        
        # Reposition remaining graphs
        self.rearrange_graphs()
    
    def rearrange_graphs(self):
        """Rearrange all graphs in the grid"""
        # Remove all graphs from grid layout
        for graph in self.graphs:
            self.grid_layout.removeWidget(graph)
        
        # Re-add graphs to layout
        self.current_row = 0
        self.current_col = 0
        
        for graph in self.graphs:
            self.grid_layout.addWidget(graph, self.current_row, self.current_col)
            self.current_col += 1
            if self.current_col >= self.max_cols:
                self.current_col = 0
                self.current_row += 1
    
    def save_dashboard(self):
        """Save the current dashboard layout and settings"""
        graph_configs = []
        for graph in self.graphs:
            graph_configs.append(graph.get_config_dict())
        
        self.config["graphs"] = graph_configs
        save_config(self.config)
    
    def load_dashboard(self):
        """Load graphs from saved configuration"""
        if "graphs" not in self.config:
            return
            
        for graph_config in self.config["graphs"]:
            graph = GraphModule(
                graph_id=graph_config.get("id"),
                graph_type=graph_config.get("type", "line"),
                title=graph_config.get("title", "Graph"),
                config=graph_config.get("config", {})
            )
            graph.removed.connect(self.remove_graph)
            
            # Add to grid layout
            self.grid_layout.addWidget(graph, self.current_row, self.current_col)
            
            # Update grid position for next graph
            self.current_col += 1
            if self.current_col >= self.max_cols:
                self.current_col = 0
                self.current_row += 1
            
            self.graphs.append(graph)

def config_UI(strategy_path=None):
    """Main function to run the Graph Dashboard"""
    app = pg.mkQApp("Graph Dashboard")
    dashboard = GraphDashboard()
    dashboard.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    config_UI()