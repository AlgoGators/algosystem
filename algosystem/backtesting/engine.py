import pandas as pd
import numpy as np
import os
import shutil
import json
import webbrowser
import matplotlib.pyplot as plt

from algosystem.utils._logging import get_logger
from algosystem.backtesting.visualization import (
    create_equity_chart,
    create_drawdown_chart,
    create_monthly_returns_heatmap,
    create_rolling_sharpe_chart
)

from algosystem.backtesting import metrics

logger = get_logger(__name__)

class Engine:
    """Backtesting engine that uses a price series (e.g. portfolio value) as input."""
    
    def __init__(self, data, benchmark, start_date=None, end_date=None, 
                 initial_capital=None, price_column=None):
        """
        Initialize the backtesting engine using a price series.
        
        Parameters:
        -----------
        data : pd.DataFrame or pd.Series
            Historical data of the strategy’s portfolio value.
            If a DataFrame is provided, you must either pass a price_column or ensure it has one column.
        start_date : str, optional
            Start date for the backtest (YYYY-MM-DD). Defaults to the first date in data.
        end_date : str, optional
            End date for the backtest (YYYY-MM-DD). Defaults to the last date in data.
        initial_capital : float, optional
            Initial capital. If not provided, inferred as the first value of the price series.
        price_column : str, optional
            If data is a DataFrame with multiple columns, specify the column name representing
            portfolio value.
        """
        # Support for DataFrame or Series input
        if isinstance(data, pd.DataFrame):
            if price_column is not None:
                self.price_series = data[price_column].copy()
            else:
                if data.shape[1] == 1:
                    self.price_series = data.iloc[:, 0].copy()
                else:
                    raise ValueError("DataFrame has multiple columns; specify price_column.")
        elif isinstance(data, pd.Series):
            self.price_series = data.copy()
        else:
            raise TypeError("data must be a pandas DataFrame or Series")
        
        
        self.benchmark_series = benchmark.copy() if benchmark is not None else None

        # Set date range based on provided dates or available index
        self.start_date = pd.to_datetime(start_date) if start_date else self.price_series.index[0]
        self.end_date = pd.to_datetime(end_date) if end_date else self.price_series.index[-1]
        mask = (self.price_series.index >= self.start_date) & (self.price_series.index <= self.end_date)
        self.price_series = self.price_series.loc[mask]
        
        if self.price_series.empty:
            raise ValueError("No data available for the specified date range")
        
        # Use the provided initial_capital or infer it from the first value
        self.initial_capital = initial_capital if initial_capital is not None else self.price_series.iloc[0]
        
        self.results = None
        self.metrics = None
        self.plots = None

        logger.info(f"Initialized backtest from {self.start_date.date()} to {self.end_date.date()}")
        
    def run(self):
        """
        Run the backtest simulation.
        
        Since the input data is already the price series of your strategy, 
        we interpret the data as the evolution of portfolio value. The engine
        normalizes the price series with respect to the first day, then scales it
        by the initial capital.
        
        Returns:
        --------
        results : dict
            Dictionary containing backtest results.
        """
        logger.info("Starting backtest simulation")
        
        # Normalize the price series relative to its first value and scale by initial capital.
        equity_series = self.initial_capital * (self.price_series / self.price_series.iloc[0])

        logger.info("Calculating performance metrics")
        self.metrics = metrics.calculate_metrics(equity_series, self.benchmark_series)

        logger.info("Generating performance plots")
        # Fix: Pass benchmark_series instead of initial_capital
        self.plots = metrics.calculate_time_series_data(equity_series, self.benchmark_series)
        
        self.results = {
            'equity': equity_series,
            # Positions and trades are not computed in this model because the data
            # represents the final portfolio value. If desired, you can derive additional metrics.
            'initial_capital': self.initial_capital,
            'final_capital': equity_series.iloc[-1],
            'returns': (equity_series.iloc[-1] - self.initial_capital) / self.initial_capital,
            'data': self.price_series,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'metrics': self.metrics,
            'plots': self.plots,
        }
        
        logger.info(f"Backtest completed. Final return: {self.results['returns']:.2%}")
        return self.results
    
    def get_results(self):
        return self.results

    def get_metrics(self):
        return self.metrics
    
    def print_metrics(self):
        """
        Print performance metrics to console.
        """
        metrics = self.get_metrics()
        logger.info("Performance Metrics:")
        for key, value in metrics.items():
            logger.info(f"{key}: {value}")
    
    def get_plots(self, output_path=None, show_charts=True):
        """
        Generate, save, and return performance plots.

        Parameters:
        -----------
        output_path : str, optional
            Directory in which to save the plots.
            If not provided, defaults to a subfolder named 'plots' in the current working directory.
        show_charts : bool, optional
            If True, display the charts interactively. If False, the charts will not be shown.

        Returns:
        --------
        plots : dict
            Dictionary containing matplotlib figure objects for each plot.
        """
        # Extract the equity series from the results for those plots that require it:
        equity_series = self.results['equity']

        equity_chart = create_equity_chart(equity_series)
        drawdown_chart = create_drawdown_chart(equity_series)
        monthly_returns_heatmap = create_monthly_returns_heatmap(equity_series)
        rolling_sharpe_chart = create_rolling_sharpe_chart(equity_series)

        plots = {
            'equity_chart': equity_chart,
            'drawdown_chart': drawdown_chart,
            'monthly_returns_heatmap': monthly_returns_heatmap,
            'rolling_sharpe_chart': rolling_sharpe_chart
        }

        # Set default output path if none provided; default to "./plots"
        if output_path is None:
            output_path = os.path.join(os.getcwd(), "plots")
        else:
            output_path = os.path.abspath(output_path)

        # Create the directory if it doesn't exist.
        os.makedirs(output_path, exist_ok=True)

        # Save each plot to a separate PNG file.
        for key, fig in plots.items():
            file_path = os.path.join(output_path, f"{key}.png")
            fig.savefig(file_path)
            print(f"Saved {key} to {file_path}")

        # If show_charts is True, display the plots interactively.
        if show_charts:
            # Turn interactive mode off to force blocking behavior.
            plt.ioff()
            # This call will block until all open figure windows are closed.
            plt.show(block=True)

        return plots
    
    def _format_time_series(self, series):
        """Format a time series for the dashboard"""
        if series is None or series.empty:
            return []
        
        result = []
        for date, value in series.items():
            # Convert date to string
            date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
            
            # Handle NumPy types
            if isinstance(value, (np.integer, np.floating)):
                value_float = float(value.item())
            else:
                value_float = float(value) if pd.notna(value) else None
            
            result.append({'date': date_str, 'value': value_float})
        
        return result


    def generate_dashboard(self, output_dir=None, open_browser=True, config_path=None):
        """
        Generate an HTML dashboard for the backtest results using graph_config.json
        
        Parameters:
        -----------
        output_dir : str, optional
            Directory where dashboard files will be saved. Defaults to ./dashboard/
        open_browser : bool, optional
            Whether to automatically open the dashboard in browser. Defaults to True
        config_path : str, optional
            Path to the graph configuration file. Defaults to utils/graph_config.json
            
        Returns:
        --------
        dashboard_path : str
            Path to the generated dashboard HTML file
        """
        # Get results from the engine
        if self.results is None:
            raise ValueError("No backtest results available. Run the backtest first.")
        
        # Set default output directory
        if output_dir is None:
            output_dir = os.path.join(os.getcwd(), "dashboard")
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Load graph configuration
        if config_path is None:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "utils", "graph_config.json")
        
        with open(config_path, 'r') as f:
            graph_config = json.load(f)
        
        # Extract plot configurations
        plots = graph_config.get('plots', [])
        max_cols = graph_config.get('max_cols', 2)
        
        # Generate HTML dashboard
        dashboard_html = self._generate_dashboard_html(plots, max_cols)
        
        # Write dashboard files
        dashboard_path = os.path.join(output_dir, 'dashboard.html')
        with open(dashboard_path, 'w') as f:
            f.write(dashboard_html)
        
        # Prepare and save the data for the dashboard
        dashboard_data = self.prepare_dashboard_data()
        data_path = os.path.join(output_dir, 'dashboard_data.json')
        with open(data_path, 'w') as f:
            json.dump(dashboard_data, f, indent=2)
        
        # Create the CSS file
        css_path = os.path.join(output_dir, 'dashboard.css')
        with open(css_path, 'w') as f:
            f.write(self._get_dashboard_css())
        
        # Open in browser if requested
        if open_browser:
            webbrowser.open('file://' + os.path.abspath(dashboard_path))
        
        return dashboard_path

    def _generate_dashboard_html(self, plots, max_cols):
        """Generate HTML for the dashboard based on plot configuration"""
        
        # Get basic metrics
        metrics = self.results.get('metrics', {})
        
        # Convert metrics to standard Python types for JSON serialization
        serializable_metrics = {}
        for key, value in metrics.items():
            if isinstance(value, (np.integer, np.floating, np.bool_)):
                serializable_metrics[key] = value.item()  # Convert NumPy types to Python native types
            else:
                serializable_metrics[key] = value
        
        total_return = float(self.results.get('returns', 0) * 100)  # Convert to percentage
        
        # Generate metrics HTML
        metrics_html = """
        <div class="metrics-grid">
            <div class="metric-card">
                <p class="metric-title">Annualized Return</p>
                <p class="metric-value" id="annualizedReturn">{:.2f}%</p>
            </div>
            <div class="metric-card">
                <p class="metric-title">Volatility</p>
                <p class="metric-value" id="volatility">{:.2f}%</p>
            </div>
            <div class="metric-card">
                <p class="metric-title">Sharpe Ratio</p>
                <p class="metric-value" id="sharpeRatio">{:.2f}</p>
            </div>
            <div class="metric-card">
                <p class="metric-title">Max Drawdown</p>
                <p class="metric-value" id="maxDrawdown">{:.2f}%</p>
            </div>
        </div>
        """.format(
            serializable_metrics.get('annual_return', 0) * 100,
            serializable_metrics.get('volatility', 0) * 100,
            serializable_metrics.get('sharpe_ratio', 0),
            serializable_metrics.get('max_drawdown', 0) * 100
        )
        
        # Sort plots by row and column
        sorted_plots = sorted(plots, key=lambda p: (p.get('position', {}).get('row', 0), p.get('position', {}).get('col', 0)))
        
        # Generate plots HTML
        plots_html = '<div class="plots-grid">'
        
        # Group plots by row
        current_row = -1
        for plot in sorted_plots:
            row = plot.get('position', {}).get('row', 0)
            
            # If new row, close previous row div and start new one
            if row != current_row:
                if current_row != -1:
                    plots_html += '</div>'  # Close previous row
                plots_html += f'<div class="plot-row">'
                current_row = row
            
            # Add plot div with appropriate ID
            plot_id = f"plot_{plot.get('id', '')}"
            plot_title = plot.get('title', plot.get('type', 'Plot'))
            plots_html += f"""
            <div class="plot-card">
                <h3 class="plot-title">{plot_title}</h3>
                <div id="{plot_id}" class="plot-container"></div>
            </div>
            """
        
        # Close the last row and the plots grid
        plots_html += '</div></div>'
        
        # Generate JavaScript to create the plots
        js = f"""
        <script>
        // Dashboard data
        const dashboardData = {{
            equity: {self._convert_series_to_js(self.results.get('equity', pd.Series()))},
            returns: {self._convert_series_to_js(self.results['equity'].pct_change().dropna() if 'equity' in self.results else pd.Series())},
            metrics: {json.dumps(serializable_metrics)},
            startDate: "{self.results.get('start_date', '').strftime('%Y-%m-%d') if 'start_date' in self.results else ''}",
            endDate: "{self.results.get('end_date', '').strftime('%Y-%m-%d') if 'end_date' in self.results else ''}",
            totalReturn: {total_return}
        }};
        
        // Create charts when document is loaded
        document.addEventListener('DOMContentLoaded', function() {{
            // Create header with summary
            document.getElementById('totalReturn').textContent = 
                (dashboardData.totalReturn >= 0 ? '+' : '') + dashboardData.totalReturn.toFixed(2) + '%';
            document.getElementById('totalReturn').className = 
                dashboardData.totalReturn >= 0 ? 'positive-return' : 'negative-return';
            
            document.getElementById('dateRange').textContent = 
                'Backtest Period: ' + dashboardData.startDate + ' to ' + dashboardData.endDate;
            
            // Create plots
        """
        
        # Add code to create each plot based on chart.js
        for plot in sorted_plots:
            plot_id = f"plot_{plot.get('id', '')}"
            plot_type = plot.get('type', '')
            
            if plot_type == 'Equity Curve':
                js += f"""
                createEquityCurveChart('{plot_id}');
                """
            elif plot_type == 'Drawdown Chart':
                js += f"""
                createDrawdownChart('{plot_id}');
                """
            elif plot_type == 'Monthly Returns Heatmap':
                js += f"""
                createMonthlyReturnsHeatmap('{plot_id}');
                """
            elif plot_type == 'Rolling Sharpe Ratio':
                window = plot.get('config', {}).get('window_size', 252)
                js += f"""
                createRollingSharpeChart('{plot_id}', {window});
                """
        
        # Close the JavaScript code and add chart functions
        js += """
        });
        
        // Chart creation functions
        function createEquityCurveChart(containerId) {
            const container = document.getElementById(containerId);
            const canvas = document.createElement('canvas');
            container.appendChild(canvas);
            
            // Prepare data for Chart.js
            const dates = dashboardData.equity.map(item => item[0]);
            const values = dashboardData.equity.map(item => item[1]);
            
            new Chart(canvas, {
                type: 'line',
                data: {
                    labels: dates,
                    datasets: [{
                        label: 'Strategy',
                        data: values,
                        borderColor: '#2ecc71',
                        backgroundColor: 'rgba(46, 204, 113, 0.1)',
                        fill: true,
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        tooltip: {
                            mode: 'index',
                            intersect: false
                        },
                        legend: {
                            position: 'top'
                        }
                    },
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                unit: 'month'
                            },
                            title: {
                                display: true,
                                text: 'Date'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Value ($)'
                            }
                        }
                    }
                }
            });
        }
        
        function createDrawdownChart(containerId) {
            const container = document.getElementById(containerId);
            const canvas = document.createElement('canvas');
            container.appendChild(canvas);
            
            // Calculate drawdown from equity
            const equityData = dashboardData.equity;
            const drawdown = [];
            
            let peak = 0;
            for (let i = 0; i < equityData.length; i++) {
                const [date, value] = equityData[i];
                if (i === 0 || value > peak) {
                    peak = value;
                }
                const dd = (value / peak) - 1;
                drawdown.push([date, dd]);
            }
            
            const dates = drawdown.map(item => item[0]);
            const values = drawdown.map(item => item[1]);
            
            new Chart(canvas, {
                type: 'line',
                data: {
                    labels: dates,
                    datasets: [{
                        label: 'Drawdown',
                        data: values,
                        borderColor: '#e74c3c',
                        backgroundColor: 'rgba(231, 76, 60, 0.1)',
                        fill: true,
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                label: function(context) {
                                    return `${(context.raw * 100).toFixed(2)}%`;
                                }
                            }
                        },
                        legend: {
                            position: 'top'
                        }
                    },
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                unit: 'month'
                            },
                            title: {
                                display: true,
                                text: 'Date'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Drawdown (%)'
                            },
                            ticks: {
                                callback: function(value) {
                                    return `${(value * 100).toFixed(0)}%`;
                                }
                            }
                        }
                    }
                }
            });
        }
        
        function createMonthlyReturnsHeatmap(containerId) {
            const container = document.getElementById(containerId);
            
            // Calculate monthly returns from equity
            const equityData = dashboardData.equity;
            const monthlyReturns = {};
            
            let lastMonthDate = null;
            let lastMonthValue = null;
            
            for (let i = 0; i < equityData.length; i++) {
                const [dateStr, value] = equityData[i];
                const date = new Date(dateStr);
                const yearMonth = `${date.getFullYear()}-${date.getMonth()+1}`;
                
                // If this is a new month, calculate return
                if (lastMonthDate && new Date(lastMonthDate).getMonth() !== date.getMonth()) {
                    const prevYearMonth = `${new Date(lastMonthDate).getFullYear()}-${new Date(lastMonthDate).getMonth()+1}`;
                    if (!monthlyReturns[prevYearMonth]) {
                        monthlyReturns[prevYearMonth] = {
                            year: new Date(lastMonthDate).getFullYear(),
                            month: new Date(lastMonthDate).getMonth()+1,
                            value: lastMonthValue
                        };
                    }
                }
                
                lastMonthDate = dateStr;
                lastMonthValue = value;
            }
            
            // Create heatmap table
            const table = document.createElement('table');
            table.className = 'monthly-returns-table';
            container.appendChild(table);
            
            // Add header row with month names
            const headerRow = document.createElement('tr');
            table.appendChild(headerRow);
            
            const cornerCell = document.createElement('th');
            headerRow.appendChild(cornerCell);
            
            const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
            months.forEach(month => {
                const th = document.createElement('th');
                th.textContent = month;
                headerRow.appendChild(th);
            });
            
            // Create a row for each year
            const years = [...new Set(Object.values(monthlyReturns).map(item => item.year))].sort();
            
            years.forEach(year => {
                const row = document.createElement('tr');
                table.appendChild(row);
                
                const yearCell = document.createElement('th');
                yearCell.textContent = year;
                row.appendChild(yearCell);
                
                // Add cells for each month
                for (let month = 1; month <= 12; month++) {
                    const td = document.createElement('td');
                    row.appendChild(td);
                    
                    const key = `${year}-${month}`;
                    if (monthlyReturns[key]) {
                        const monthData = monthlyReturns[key];
                        const prevMonthKey = month > 1 ? `${year}-${month-1}` : `${year-1}-12`;
                        const prevMonthData = monthlyReturns[prevMonthKey];
                        
                        if (prevMonthData) {
                            const monthlyReturn = (monthData.value / prevMonthData.value) - 1;
                            td.textContent = `${(monthlyReturn * 100).toFixed(1)}%`;
                            
                            // Color based on return
                            if (monthlyReturn > 0.03) {
                                td.style.backgroundColor = 'rgba(46, 204, 113, 0.8)';
                                td.style.color = 'white';
                            } else if (monthlyReturn > 0.01) {
                                td.style.backgroundColor = 'rgba(46, 204, 113, 0.5)';
                            } else if (monthlyReturn > 0) {
                                td.style.backgroundColor = 'rgba(46, 204, 113, 0.2)';
                            } else if (monthlyReturn > -0.01) {
                                td.style.backgroundColor = 'rgba(231, 76, 60, 0.2)';
                            } else if (monthlyReturn > -0.03) {
                                td.style.backgroundColor = 'rgba(231, 76, 60, 0.5)';
                            } else {
                                td.style.backgroundColor = 'rgba(231, 76, 60, 0.8)';
                                td.style.color = 'white';
                            }
                        }
                    }
                }
            });
        }
        
        function createRollingSharpeChart(containerId, window) {
            const container = document.getElementById(containerId);
            const canvas = document.createElement('canvas');
            container.appendChild(canvas);
            
            // Calculate rolling Sharpe from returns (simplified approach)
            const returnsData = dashboardData.returns;
            const annualizationFactor = 252; // Trading days in a year
            const rollingWindow = window || 252; // Default to 1 year
            
            // Simple rolling calculation for sharpe ratio
            const sharpeRatio = [];
            for (let i = rollingWindow - 1; i < returnsData.length; i++) {
                const windowReturns = returnsData.slice(i - rollingWindow + 1, i + 1).map(item => item[1]);
                
                const meanReturn = windowReturns.reduce((sum, val) => sum + val, 0) / windowReturns.length;
                const annualizedReturn = meanReturn * annualizationFactor;
                
                // Calculate standard deviation
                const variance = windowReturns.reduce((sum, val) => sum + Math.pow(val - meanReturn, 2), 0) / windowReturns.length;
                const stdDev = Math.sqrt(variance);
                const annualizedStdDev = stdDev * Math.sqrt(annualizationFactor);
                
                // Calculate Sharpe ratio (assuming risk-free rate = 0)
                const sharpe = annualizedStdDev === 0 ? 0 : annualizedReturn / annualizedStdDev;
                
                sharpeRatio.push([returnsData[i][0], sharpe]);
            }
            
            const dates = sharpeRatio.map(item => item[0]);
            const values = sharpeRatio.map(item => item[1]);
            
            new Chart(canvas, {
                type: 'line',
                data: {
                    labels: dates,
                    datasets: [{
                        label: `${window}-Day Rolling Sharpe`,
                        data: values,
                        borderColor: '#9b59b6',
                        backgroundColor: 'rgba(155, 89, 182, 0.1)',
                        fill: true,
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        tooltip: {
                            mode: 'index',
                            intersect: false
                        },
                        legend: {
                            position: 'top'
                        }
                    },
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                unit: 'month'
                            },
                            title: {
                                display: true,
                                text: 'Date'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Sharpe Ratio'
                            }
                        }
                    }
                }
            });
        }
        </script>
        """
        
        # Assemble the complete HTML
        html = f"""<!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>AlgoSystem Trading Dashboard</title>
            <style>
            /* Dashboard styles */
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 0;
                background-color: #f5f7fa;
                color: #333;
            }}
            
            .container {{
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
            }}
            
            .header {{
                background-color: #2c3e50;
                color: white;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}
            
            .header h1 {{
                margin: 0;
                font-size: 24px;
            }}
            
            .date-range {{
                font-size: 14px;
                opacity: 0.8;
            }}
            
            .positive-return {{
                color: #2ecc71;
                font-size: 28px;
                font-weight: bold;
                margin: 0;
            }}
            
            .negative-return {{
                color: #e74c3c;
                font-size: 28px;
                font-weight: bold;
                margin: 0;
            }}
            
            /* Metrics grid */
            .metrics-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                grid-gap: 20px;
                margin-bottom: 20px;
            }}
            
            .metric-card {{
                background-color: white;
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }}
            
            .metric-title {{
                font-size: 14px;
                color: #7f8c8d;
                margin: 0 0 5px 0;
            }}
            
            .metric-value {{
                font-size: 24px;
                font-weight: bold;
                margin: 0;
            }}
            
            /* Plots grid */
            .plots-grid {{
                display: flex;
                flex-direction: column;
                gap: 20px;
            }}
            
            .plot-row {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                grid-gap: 20px;
            }}
            
            .plot-card {{
                background-color: white;
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }}
            
            .plot-title {{
                font-size: 18px;
                margin-top: 0;
                margin-bottom: 15px;
            }}
            
            .plot-container {{
                height: 300px;
                width: 100%;
            }}
            
            /* Monthly returns table */
            .monthly-returns-table {{
                width: 100%;
                border-collapse: collapse;
            }}
            
            .monthly-returns-table th,
            .monthly-returns-table td {{
                padding: 8px;
                text-align: center;
                border: 1px solid #ddd;
            }}
            
            /* Responsive layout */
            @media (max-width: 768px) {{
                .plot-row {{
                    grid-template-columns: 1fr;
                }}
                
                .header {{
                    flex-direction: column;
                    align-items: flex-start;
                }}
                
                .header > div:last-child {{
                    margin-top: 15px;
                }}
            }}
            </style>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/moment.js/2.29.4/moment.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/chartjs-adapter-moment/1.0.1/chartjs-adapter-moment.min.js"></script>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div>
                        <h1>AlgoSystem Trading Dashboard</h1>
                        <div class="date-range" id="dateRange">Backtest Period: Loading...</div>
                    </div>
                    <div>
                        <h2 id="totalReturn" class="positive-return">Loading...</h2>
                        <p class="metric-title">Total Return</p>
                    </div>
                </div>
                
                {metrics_html}
                
                {plots_html}
            </div>
            
            {js}
        </body>
        </html>
        """
        
        return html
    
    def _convert_series_to_js(self, series):
        """Convert pandas Series to JavaScript-friendly format"""
        if series.empty:
            return "[]"
        
        # Convert series to list of [date, value] pairs
        data = []
        for date, value in series.items():
            # Format date as ISO string and ensure value is a number
            date_str = date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date)
            
            # Handle NumPy types
            if isinstance(value, (np.integer, np.floating)):
                value_float = float(value.item())
            else:
                value_float = float(value) if pd.notna(value) else None
            
            data.append([date_str, value_float])
        
        return json.dumps(data)

    def _get_dashboard_css(self):
        """Return CSS for the dashboard"""
        return """
        /* Dashboard styles */
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f7fa;
            color: #333;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background-color: #2c3e50;
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 {
            margin: 0;
            font-size: 24px;
        }
        
        .date-range {
            font-size: 14px;
            opacity: 0.8;
        }
        
        .total-return {
            font-size: 32px;
            font-weight: bold;
            margin: 0;
        }
        
        .positive-return {
            color: #2ecc71;
        }
        
        .negative-return {
            color: #e74c3c;
        }
        
        /* Metrics grid */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            grid-gap: 20px;
            margin-bottom: 20px;
        }
        
        .metric-card {
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .metric-title {
            font-size: 14px;
            color: #7f8c8d;
            margin: 0 0 5px 0;
        }
        
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            margin: 0;
        }
        
        /* Plots grid */
        .plots-grid {
            display: flex;
            flex-direction: column;
            gap: 20px;
        }
        
        .plot-row {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            grid-gap: 20px;
        }
        
        .plot-card {
            background-color: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .plot-title {
            font-size: 18px;
            margin-top: 0;
            margin-bottom: 15px;
        }
        
        .plot-container {
            height: 300px;
            width: 100%;
        }
        
        /* Responsive layout */
        @media (max-width: 768px) {
            .plot-row {
                grid-template-columns: 1fr;
            }
            
            .header {
                flex-direction: column;
                align-items: flex-start;
            }
            
            .header > div:last-child {
                margin-top: 15px;
            }
        }
        """

    def prepare_dashboard_data(self):
        """
        Prepare backtest results data for the dashboard
        
        Returns:
        --------
        dashboard_data : dict
            Formatted data ready for the dashboard
        """
        if self.results is None:
            raise ValueError("No backtest results available. Run the backtest first.")
        
        # Extract metrics and ensure they're serializable
        metrics = {}
        for key, value in self.results.get('metrics', {}).items():
            if isinstance(value, (np.integer, np.floating, np.bool_)):
                metrics[key] = value.item()  # Convert NumPy types to Python native types
            else:
                metrics[key] = value
        
        # Format time series data
        formatted_data = {}
        
        # Add equity curve
        if 'equity' in self.results:
            equity = self.results['equity']
            formatted_data['equity'] = self._format_time_series(equity)
        
        # Add benchmark if available
        plots = self.results.get('plots', {})
        if 'benchmark_equity_curve' in plots:
            benchmark = plots['benchmark_equity_curve']
            formatted_data['benchmark'] = self._format_time_series(benchmark)
        
        # Add drawdown
        if 'drawdown_series' in plots:
            drawdown = plots['drawdown_series']
            formatted_data['drawdown'] = self._format_time_series(drawdown)
        
        # Add rolling sharpe
        if 'rolling_sharpe' in plots:
            rolling_sharpe = plots['rolling_sharpe']
            formatted_data['rolling_sharpe'] = self._format_time_series(rolling_sharpe)
        
        # Add monthly returns
        if 'monthly_returns' in plots:
            monthly_returns = plots['monthly_returns']
            formatted_data['monthly_returns'] = self._format_time_series(monthly_returns)
        
        # Return the dashboard data
        return {
            'metrics': metrics,
            'data': formatted_data,
            'start_date': self.start_date.strftime('%Y-%m-%d'),
            'end_date': self.end_date.strftime('%Y-%m-%d'),
            'total_return': float(self.results.get('returns', 0)) * 100  # Convert to percentage
        }
