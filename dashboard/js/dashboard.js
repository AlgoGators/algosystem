/**
 * Dashboard - Main dashboard functionality
 */

// Global data object
let chartData;

/**
 * Initialize the dashboard
 */
function initDashboard() {
    // Load data
    fetch('dashboard_data.json')
        .then(response => response.json())
        .then(data => {
            // Store data globally
            chartData = data;
            
            // Initialize dashboard components
            createDashboard();
        })
        .catch(error => {
            console.error('Error loading dashboard data:', error);
            document.body.innerHTML = `<div class="error-message">Error loading dashboard data: ${error.message}</div>`;
        });
}

/**
 * Create the dashboard
 */
function createDashboard() {
    // Update metadata in the header
    updateHeader();
    
    // Create metrics
    createMetrics();
    
    // Create charts
    createCharts();
    
    // Add window resize handler
    window.addEventListener('resize', handleResize);
}

/**
 * Update the dashboard header with metadata
 */
function updateHeader() {
    // Update title if needed
    const titleElement = document.querySelector('.dashboard-header h1');
    if (titleElement && chartData.metadata.title) {
        titleElement.textContent = chartData.metadata.title;
    }
    
    // Update date range
    const dateRangeElement = document.querySelector('.date-range');
    if (dateRangeElement) {
        dateRangeElement.textContent = `Backtest Period: ${chartData.metadata.start_date} to ${chartData.metadata.end_date}`;
    }
    
    // Update total return
    const totalReturnElement = document.querySelector('.header-summary h2');
    if (totalReturnElement) {
        const totalReturn = chartData.metadata.total_return;
        const sign = totalReturn >= 0 ? '+' : '';
        totalReturnElement.textContent = `${sign}${totalReturn.toFixed(2)}%`;
        totalReturnElement.className = totalReturn >= 0 ? 'positive-return' : 'negative-return';
    }
}

/**
 * Create metrics based on data
 */
function createMetrics() {
    // Check if metrics data is available
    if (!chartData.metrics) return;
    
    // Update each metric
    for (const metricId in chartData.metrics) {
        const metric = chartData.metrics[metricId];
        
        // Update based on metric type
        switch (metric.type) {
            case 'Percentage':
                updatePercentageMetric(metricId, metric.value);
                break;
            case 'Value':
                updateValueMetric(metricId, metric.value);
                break;
            case 'Currency':
                updateCurrencyMetric(metricId, metric.value);
                break;
            default:
                // Unsupported metric type
                console.warn(`Unsupported metric type: ${metric.type}`);
        }
    }
}

/**
 * Create charts based on data
 */
function createCharts() {
    // Check if charts data is available
    if (!chartData.charts) return;
    
    // Create each chart
    for (const chartId in chartData.charts) {
        const chart = chartData.charts[chartId];
        
        // Create based on chart type
        switch (chart.type) {
            case 'LineChart':
                createLineChart(
                    chartId,
                    chart.data,
                    getChartOptions(chart)
                );
                break;
            case 'HeatmapTable':
                createHeatmapTable(
                    chartId,
                    chart.data
                );
                break;
            default:
                // Unsupported chart type
                console.warn(`Unsupported chart type: ${chart.type}`);
        }
    }
}

/**
 * Get chart options based on chart configuration
 * @param {object} chart - Chart configuration
 * @returns {object} - Chart options
 */
function getChartOptions(chart) {
    // Base options
    const options = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                display: true,
                position: 'top',
            },
            tooltip: {
                mode: 'index',
                intersect: false
            }
        },
        scales: {
            x: {
                type: 'time',
                time: {
                    unit: 'month',
                    displayFormats: {
                        month: 'MMM YYYY'
                    }
                },
                title: {
                    display: true,
                    text: 'Date'
                }
            },
            y: {
                title: {
                    display: true,
                    text: chart.config.y_axis_label || 'Value'
                }
            }
        }
    };
    
    // Add percentage formatting if needed
    if (chart.config.percentage_format) {
        options.plugins.tooltip.callbacks = {
            label: function(context) {
                let label = context.dataset.label || '';
                if (label) {
                    label += ': ';
                }
                if (context.parsed.y !== null) {
                    label += formatAsPercentage(context.parsed.y);
                }
                return label;
            }
        };
        
        options.scales.y.ticks = {
            callback: function(value) {
                return formatAsPercentage(value);
            }
        };
    }
    
    return options;
}

/**
 * Handle window resize event
 */
function handleResize() {
    // Redraw charts if needed
    for (const chartId in chartInstances) {
        if (chartInstances[chartId]) {
            chartInstances[chartId].resize();
        }
    }
}