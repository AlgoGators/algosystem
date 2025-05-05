// Main JavaScript file for the AlgoSystem Trading Dashboard

// This will store all dashboard data
let dashboardData = null;

// Fetch the metrics data from the JSON file
async function fetchDashboardData() {
    try {
        const response = await fetch('dashboard_data.json');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        dashboardData = await response.json();
        
        // Update the dashboard with the data
        updateDashboard();
    } catch (error) {
        console.error('Error fetching dashboard data:', error);
        document.body.innerHTML = `<div class="container">
            <div class="chart-container">
                <h3 class="chart-title">Error Loading Dashboard</h3>
                <p>Could not load dashboard data. Error: ${error.message}</p>
                <p>Please make sure dashboard_data.json is available in the same directory.</p>
            </div>
        </div>`;
    }
}

// Update all dashboard elements with the data
function updateDashboard() {
    if (!dashboardData) return;
    
    // Update header information
    document.getElementById('dateRange').textContent = 
        `Backtest Period: ${dashboardData.startDate} - ${dashboardData.endDate}`;
    
    const finalReturn = document.getElementById('finalReturn');
    finalReturn.textContent = 
        `${dashboardData.finalReturn > 0 ? '+' : ''}${dashboardData.finalReturn.toFixed(2)}%`;
    finalReturn.className = `metric-value ${dashboardData.finalReturn >= 0 ? 'positive' : 'negative'}`;
    
    // Update metrics
    updateMetrics();
    
    // Create charts
    createCharts();
}

// Update the metrics cards with data
function updateMetrics() {
    const metrics = dashboardData.metrics;
    
    // Update each metric card
    if (metrics.annualized_return !== undefined) {
        const element = document.getElementById('annualizedReturn');
        element.textContent = `${metrics.annualized_return.toFixed(2)}%`;
        element.className = `metric-value ${metrics.annualized_return >= 0 ? 'positive' : 'negative'}`;
    }
    
    if (metrics.annualized_volatility !== undefined) {
        document.getElementById('annualizedVolatility').textContent = 
            `${metrics.annualized_volatility.toFixed(2)}%`;
    }
    
    if (metrics.sharpe_ratio !== undefined) {
        document.getElementById('sharpeRatio').textContent = 
            metrics.sharpe_ratio.toFixed(2);
    }
    
    if (metrics.sortino_ratio !== undefined) {
        document.getElementById('sortinoRatio').textContent = 
            metrics.sortino_ratio.toFixed(2);
    }
    
    if (metrics.max_drawdown !== undefined) {
        document.getElementById('maxDrawdown').textContent = 
            `${metrics.max_drawdown.toFixed(2)}%`;
    }
    
    if (metrics.calmar_ratio !== undefined) {
        document.getElementById('calmarRatio').textContent = 
            metrics.calmar_ratio.toFixed(2);
    }
    
    if (metrics.alpha !== undefined) {
        const element = document.getElementById('alpha');
        element.textContent = `${metrics.alpha.toFixed(2)}%`;
        element.className = `metric-value ${metrics.alpha >= 0 ? 'positive' : 'negative'}`;
    }
    
    if (metrics.beta !== undefined) {
        document.getElementById('beta').textContent = 
            metrics.beta.toFixed(2);
    }
    
    // Update trading statistics
    if (metrics.pct_positive_days !== undefined) {
        document.getElementById('winRate').textContent = 
            `${metrics.pct_positive_days.toFixed(2)}%`;
    }
    
    if (metrics.best_month !== undefined) {
        document.getElementById('bestMonth').textContent = 
            `+${metrics.best_month.toFixed(2)}%`;
    }
    
    if (metrics.worst_month !== undefined) {
        document.getElementById('worstMonth').textContent = 
            `${metrics.worst_month.toFixed(2)}%`;
    }
}

// Create all charts for the dashboard
function createCharts() {
    const timeSeries = dashboardData.timeSeries;
    
    // Helper function to parse dates
    const parseDates = (dateStrings) => dateStrings.map(d => new Date(d));
    
    // Create Equity Curve Chart
    if (timeSeries.equity_curve && timeSeries.benchmark_equity_curve) {
        const equityCurveCtx = document.getElementById('equityCurveChart').getContext('2d');
        new Chart(equityCurveCtx, {
            type: 'line',
            data: {
                labels: parseDates(timeSeries.equity_curve.dates),
                datasets: [
                    {
                        label: 'Strategy',
                        data: timeSeries.equity_curve.values,
                        borderColor: '#2ecc71',
                        backgroundColor: 'rgba(46, 204, 113, 0.1)',
                        fill: true,
                        tension: 0.1
                    },
                    {
                        label: 'Benchmark',
                        data: timeSeries.benchmark_equity_curve.values,
                        borderColor: '#3498db',
                        backgroundColor: 'rgba(52, 152, 219, 0.1)',
                        fill: true,
                        tension: 0.1,
                        borderDash: [5, 5]
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'month'
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
    
    // Create Drawdown Chart
    if (timeSeries.drawdown_series) {
        const drawdownCtx = document.getElementById('drawdownChart').getContext('2d');
        new Chart(drawdownCtx, {
            type: 'line',
            data: {
                labels: parseDates(timeSeries.drawdown_series.dates),
                datasets: [{
                    label: 'Drawdown',
                    data: timeSeries.drawdown_series.values,
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
                        intersect: false
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'month'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Drawdown (%)'
                        },
                        max: 0,
                        min: Math.min(-5, Math.floor(dashboardData.metrics.max_drawdown)) // Dynamic minimum
                    }
                }
            }
        });
    }
    
    // Create Relative Performance Chart
    if (timeSeries.relative_performance) {
        const relPerfCtx = document.getElementById('relativePerformanceChart').getContext('2d');
        new Chart(relPerfCtx, {
            type: 'line',
            data: {
                labels: parseDates(timeSeries.relative_performance.dates),
                datasets: [{
                    label: 'Outperformance vs Benchmark',
                    data: timeSeries.relative_performance.values,
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
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'month'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Relative Performance (%)'
                        }
                    }
                }
            }
        });
    }
    
    // Create Rolling Volatility Chart
    if (timeSeries.rolling_volatility) {
        const rollingVolCtx = document.getElementById('rollingVolatilityChart').getContext('2d');
        new Chart(rollingVolCtx, {
            type: 'line',
            data: {
                labels: parseDates(timeSeries.rolling_volatility.dates),
                datasets: [{
                    label: '30-Day Rolling Volatility',
                    data: timeSeries.rolling_volatility.values,
                    borderColor: '#f39c12',
                    backgroundColor: 'rgba(243, 156, 18, 0.1)',
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
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'month'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Volatility (%)'
                        },
                        min: 0
                    }
                }
            }
        });
    }
    
    // Create Rolling Sharpe Chart
    if (timeSeries.rolling_sharpe) {
        const rollingSharpCtx = document.getElementById('rollingSharpChart').getContext('2d');
        new Chart(rollingSharpCtx, {
            type: 'line',
            data: {
                labels: parseDates(timeSeries.rolling_sharpe.dates),
                datasets: [{
                    label: '60-Day Rolling Sharpe',
                    data: timeSeries.rolling_sharpe.values,
                    borderColor: '#1abc9c',
                    backgroundColor: 'rgba(26, 188, 156, 0.1)',
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
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'month'
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
    
    // Create Rolling VaR Chart
    if (timeSeries.rolling_var) {
        const rollingVarCtx = document.getElementById('rollingVarChart').getContext('2d');
        new Chart(rollingVarCtx, {
            type: 'line',
            data: {
                labels: parseDates(timeSeries.rolling_var.dates),
                datasets: [{
                    label: '95% VaR (1-day)',
                    data: timeSeries.rolling_var.values,
                    borderColor: '#e67e22',
                    backgroundColor: 'rgba(230, 126, 34, 0.1)',
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
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'month'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Value at Risk (%)'
                        }
                    }
                }
            }
        });
    }
    
    // Create Daily Returns Distribution
    if (timeSeries.daily_returns) {
        const dailyReturnsCtx = document.getElementById('dailyReturnsChart').getContext('2d');
        
        // Create histogram data from daily returns
        const returns = timeSeries.daily_returns.values;
        const binCount = 20;
        const min = Math.min(...returns);
        const max = Math.max(...returns);
        const binWidth = (max - min) / binCount;
        
        const bins = Array(binCount).fill(0);
        const binLabels = [];
        
        for (let i = 0; i < binCount; i++) {
            const binStart = min + i * binWidth;
            const binEnd = binStart + binWidth;
            binLabels.push(`${(binStart * 100).toFixed(2)}% to ${(binEnd * 100).toFixed(2)}%`);
        }
        
        returns.forEach(ret => {
            const binIndex = Math.min(binCount - 1, Math.floor((ret - min) / binWidth));
            bins[binIndex]++;
        });
        
        new Chart(dailyReturnsCtx, {
            type: 'bar',
            data: {
                labels: binLabels,
                datasets: [{
                    label: 'Frequency',
                    data: bins,
                    backgroundColor: bins.map((_, i) => {
                        const midpoint = i / binCount;
                        if (midpoint < 0.4) return 'rgba(231, 76, 60, 0.7)';  // Red for negative returns
                        if (midpoint > 0.6) return 'rgba(46, 204, 113, 0.7)';  // Green for positive returns
                        return 'rgba(241, 196, 15, 0.7)';  // Yellow for near-zero returns
                    })
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `${context.raw} days`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Daily Return Range'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Number of Days'
                        }
                    }
                }
            }
        });
    }
    
    // Create Rolling Returns Chart
    if (timeSeries.rolling_3m_returns && timeSeries.rolling_6m_returns && timeSeries.rolling_1y_returns) {
        const rollingReturnsCtx = document.getElementById('rollingReturnsChart').getContext('2d');
        new Chart(rollingReturnsCtx, {
            type: 'line',
            data: {
                labels: parseDates(timeSeries.rolling_3m_returns.dates),
                datasets: [
                    {
                        label: '3-Month',
                        data: timeSeries.rolling_3m_returns.values,
                        borderColor: '#3498db',
                        tension: 0.1
                    },
                    {
                        label: '6-Month',
                        data: timeSeries.rolling_6m_returns.values,
                        borderColor: '#9b59b6',
                        tension: 0.1
                    },
                    {
                        label: '1-Year',
                        data: timeSeries.rolling_1y_returns.values,
                        borderColor: '#2ecc71',
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'month'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Return (%)'
                        }
                    }
                }
            }
        });
    }
    
    // Create Monthly Returns Heatmap
    createMonthlyReturnsHeatmap();
}

// Create a Monthly Returns Heatmap
function createMonthlyReturnsHeatmap() {
    const heatmapContainer = document.getElementById('monthlyReturnsHeatmap');
    if (!heatmapContainer) return;
    
    // Check if we have monthly returns data
    if (!dashboardData.timeSeries.monthly_returns) {
        heatmapContainer.innerHTML = '<p>Monthly returns data not available</p>';
        return;
    }
    
    heatmapContainer.innerHTML = '';
    
    // Create the heatmap table
    const table = document.createElement('table');
    table.className = 'monthly-returns-table';
    
    // Add header row with month names
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const headerRow = document.createElement('tr');
    
    // Empty cell for the corner
    const cornerCell = document.createElement('th');
    headerRow.appendChild(cornerCell);
    
    // Month headers
    months.forEach(month => {
        const th = document.createElement('th');
        th.textContent = month;
        headerRow.appendChild(th);
    });
    
    table.appendChild(headerRow);
    
    // Process the monthly returns data into a year/month format
    const monthlyReturns = dashboardData.timeSeries.monthly_returns;
    
    // Extract years from dates
    const years = [...new Set(monthlyReturns.dates.map(d => new Date(d).getFullYear()))].sort();
    
    // Create a row for each year
    years.forEach(year => {
        const row = document.createElement('tr');
        
        // Year cell
        const yearCell = document.createElement('td');
        yearCell.textContent = year;
        yearCell.style.fontWeight = 'bold';
        row.appendChild(yearCell);
        
        // Month cells
        for (let month = 0; month < 12; month++) {
            const td = document.createElement('td');
            
            // Find data for this year and month
            const index = monthlyReturns.dates.findIndex(d => {
                const date = new Date(d);
                return date.getFullYear() === year && date.getMonth() === month;
            });
            
            if (index !== -1) {
                const returnValue = monthlyReturns.values[index] * 100; // Convert to percentage
                td.textContent = returnValue.toFixed(1) + '%';
                
                // Color based on return value
                if (returnValue > 3) {
                    td.style.backgroundColor = 'rgba(46, 204, 113, 0.8)';
                    td.style.color = 'white';
                } else if (returnValue > 1) {
                    td.style.backgroundColor = 'rgba(46, 204, 113, 0.5)';
                } else if (returnValue > 0) {
                    td.style.backgroundColor = 'rgba(46, 204, 113, 0.2)';
                } else if (returnValue > -1) {
                    td.style.backgroundColor = 'rgba(231, 76, 60, 0.2)';
                } else if (returnValue > -3) {
                    td.style.backgroundColor = 'rgba(231, 76, 60, 0.5)';
                } else {
                    td.style.backgroundColor = 'rgba(231, 76, 60, 0.8)';
                    td.style.color = 'white';
                }
            } else {
                // If data isn't available for this month, show empty cell
                td.style.backgroundColor = '#f5f5f5';
            }
            
            row.appendChild(td);
        }
        
        table.appendChild(row);
    });
    
    heatmapContainer.appendChild(table);
}

// Tab switching functionality
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        // Remove active class from all tabs
        document.querySelectorAll('.tab').forEach(t => {
            t.classList.remove('active');
        });
        
        // Add active class to clicked tab
        tab.classList.add('active');
        
        // Hide all tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        
        // Show selected tab content
        const tabId = tab.getAttribute('data-tab');
        document.getElementById(tabId).classList.add('active');
    });
});

// Check for mobile devices and adjust layout
function checkMobile() {
    if (window.innerWidth < 768) {
        document.querySelectorAll('.metrics-grid').forEach(grid => {
            grid.style.gridTemplateColumns = '1fr';
        });
    } else {
        document.querySelectorAll('.metrics-grid').forEach(grid => {
            grid.style.gridTemplateColumns = 'repeat(auto-fill, minmax(280px, 1fr))';
        });
    }
}

// Run on load and on window resize
window.addEventListener('load', checkMobile);
window.addEventListener('resize', checkMobile);

// Initialize the dashboard
document.addEventListener('DOMContentLoaded', fetchDashboardData);