
$(document).ready(function() {

    initCategoryToggles();
    
    // Global variables
    let currentConfig = {};
    
    // Load the initial configuration
    $.getJSON('/api/config', function(config) {
        currentConfig = config;
        renderDashboard(config);
    });
    
    // Initialize drag and drop for components
    initDragAndDrop();
    
    // Add event listeners for buttons
    $('#save-config').click(saveConfiguration);
    $('#reset-config').click(resetConfiguration);
    $('#view-dashboard').click(viewDashboard);
    $('#add-metrics-row').click(addMetricsRow);
    $('#add-charts-row').click(addChartsRow);
    
    // Handle file upload
    $('#upload-form').submit(function(e) {
        e.preventDefault();
        uploadCSV();
    });
    
    // Function to render the dashboard layout
    function renderDashboard(config) {
        // Clear existing containers
        $('#metrics-container').empty();
        $('#charts-container').empty();
        
        // Render metrics rows
        if (config.metrics && config.metrics.length > 0) {
            // Group metrics by row
            const metricsByRow = {};
            config.metrics.forEach(metric => {
                const row = metric.position.row;
                if (!metricsByRow[row]) {
                    metricsByRow[row] = [];
                }
                metricsByRow[row].push(metric);
            });
            
            // Create rows and add metrics
            Object.keys(metricsByRow).sort((a, b) => parseInt(a) - parseInt(b)).forEach(row => {
                const metrics = metricsByRow[row];
                const metricsRow = $('<div class="metrics-row has-items"></div>').attr('data-row', row);
                
                // Sort metrics by column
                metrics.sort((a, b) => a.position.col - b.position.col).forEach(metric => {
                    const metricItem = createDashboardMetric(metric);
                    metricsRow.append(metricItem);
                });
                
                $('#metrics-container').append(metricsRow);
            });
        } else {
            // Add an empty row if no metrics
            addMetricsRow();
        }
        
        // Render charts rows
        if (config.charts && config.charts.length > 0) {
            // Group charts by row
            const chartsByRow = {};
            config.charts.forEach(chart => {
                const row = chart.position.row;
                if (!chartsByRow[row]) {
                    chartsByRow[row] = [];
                }
                chartsByRow[row].push(chart);
            });
            
            // Create rows and add charts
            Object.keys(chartsByRow).sort((a, b) => parseInt(a) - parseInt(b)).forEach(row => {
                const charts = chartsByRow[row];
                const chartsRow = $('<div class="charts-row has-items"></div>').attr('data-row', row);
                
                // Sort charts by column

charts.sort((a, b) => a.position.col - b.position.col).forEach(chart => {
    const chartItem = createDashboardChart(chart);
    chartsRow.append(chartItem);
});

$('#charts-container').append(chartsRow);
});
} else {
// Add an empty row if no charts
addChartsRow();
}

// Initialize sortable for newly created rows
initSortable();
}

function createDashboardMetric(metric) {
    const metricItem = $('<div class="dashboard-item dashboard-metric"></div>')
        .attr('data-id', metric.id)
        .attr('data-type', metric.type)
        .attr('data-title', metric.title)
        .attr('data-value-key', metric.value_key)
        .attr('data-col', metric.position.col);

    metricItem.append(`<div class="item-title">${metric.title}</div>`);
    metricItem.append('<div class="item-remove">×</div>');

    metricItem.removeClass('component-item metric-item');

    metricItem.find('.item-remove').click(function() {
        $(this).parent().remove();
        updateRowStatus($(this).closest('.metrics-row'));
        updateConfiguration();
    });

    return metricItem;
}

function createDashboardChart(chart) {
    const chartItem = $('<div class="dashboard-item dashboard-chart"></div>')
        .attr('data-id', chart.id)
        .attr('data-type', chart.type)
        .attr('data-title', chart.title)
        .attr('data-data-key', chart.data_key)
        .attr('data-col', chart.position.col);

    chartItem.append(`<div class="item-title">${chart.title}</div>`);
    chartItem.append('<div class="item-remove">×</div>');

    chartItem.removeClass('component-item chart-item');

    if (chart.config) {
        chartItem.attr('data-config', JSON.stringify(chart.config));
    }

    chartItem.find('.item-remove').click(function() {
        $(this).parent().remove();
        updateRowStatus($(this).closest('.charts-row'));
        updateConfiguration();
    });

    return chartItem;
}

// Function to initialize drag and drop
function initDragAndDrop() {
    // Make metric items draggable
    $('.metric-item').draggable({
        helper: 'clone',
        connectToSortable: '.metrics-row',
        revert: 'invalid'
    });

    // Make chart items draggable
    $('.chart-item').draggable({
        helper: 'clone',
        connectToSortable: '.charts-row',
        revert: 'invalid'
    });

    // Initialize sortable for existing rows
    initSortable();
}

// Function to initialize sortable rows
function initSortable() {
    // Make metrics rows sortable
    $('.metrics-row').sortable({
    tolerance: 'pointer',
    connectWith: '.metrics-row',
    placeholder: 'ui-sortable-placeholder',
    forcePlaceholderSize: true,
    receive: function(event, ui) {
        const row = $(this);

        // Check if it's a new item from the sidebar
        if (ui.item.hasClass('metric-item')) {
            const metricData = {
                id: ui.item.data('id'),
                type: ui.item.data('type'),
                title: ui.item.data('title'),
                value_key: ui.item.data('value-key'),
                position: {
                    row: parseInt(row.attr('data-row')),
                    col: row.children().length - 1
                }
            };
            
            // Create a new dashboard metric and replace the dragged item
            const newMetric = createDashboardMetric(metricData);
            
            // FIX: Explicitly remove all sidebar classes and add dashboard classes
            ui.item.removeClass('component-item metric-item ui-draggable ui-draggable-handle')
                .addClass('dashboard-item dashboard-metric');
            
            // Replace with properly styled item
            ui.item.replaceWith(newMetric);
        }

// Check if we have more than 4 metrics in a row
if (row.children().length > 4) {
    // Move the last item to a new row or the next row
    const lastItem = row.children().last();
    
    // Find the next row or create a new one
    let nextRow = row.next('.metrics-row');
    if (!nextRow.length) {
        addMetricsRow();
        nextRow = row.next('.metrics-row');
    }
    
    // Move the item
    lastItem.detach();
    nextRow.append(lastItem);
    nextRow.addClass('has-items');
}

updateRowStatus(row);
updateConfiguration();
},
update: function(event, ui) {
// Update column positions
updateColumnPositions($(this));
updateConfiguration();
}
});

// Make charts rows sortable
$('.charts-row').sortable({
tolerance: 'pointer',
connectWith: '.charts-row',
placeholder: 'ui-sortable-placeholder',
forcePlaceholderSize: true,
receive: function(event, ui) {
const row = $(this);

// Check if it's a new item from the sidebar
if (ui.item.hasClass('chart-item')) {
    const chartData = {
        id: ui.item.data('id'),
        type: ui.item.data('type'),
        title: ui.item.data('title'),
        data_key: ui.item.data('data-key'),
        position: {
            row: parseInt(row.attr('data-row')),
            col: row.children().length - 1
        },
        config: {}
    };
    
    // Create a new dashboard chart and replace the dragged item
    const newChart = createDashboardChart(chartData);
    ui.item.replaceWith(newChart);
}

// Check if we have more than 2 charts in a row
if (row.children().length > 2) {
    // Move the last item to a new row or the next row
    const lastItem = row.children().last();
    
    // Find the next row or create a new one
    let nextRow = row.next('.charts-row');
    if (!nextRow.length) {
        addChartsRow();
        nextRow = row.next('.charts-row');
    }
    
    // Move the item
    lastItem.detach();
    nextRow.append(lastItem);
    nextRow.addClass('has-items');
}

updateRowStatus(row);
updateConfiguration();
},
update: function(event, ui) {
// Update column positions
updateColumnPositions($(this));
updateConfiguration();
}
});
}

// Function to update column positions in a row
function updateColumnPositions(row) {
row.children().each(function(index) {
$(this).attr('data-col', index);
});
}

// Function to update the has-items class on a row
function updateRowStatus(row) {
if (row.children().length > 0) {
row.addClass('has-items');
} else {
row.removeClass('has-items');
}
}

// Function to add a new metrics row
function addMetricsRow() {
const rowIndex = $('.metrics-row').length;
const newRow = $('<div class="metrics-row"></div>').attr('data-row', rowIndex);
$('#metrics-container').append(newRow);

// Initialize sortable for the new row
newRow.sortable({
tolerance: 'pointer',
connectWith: '.metrics-row',
placeholder: 'ui-sortable-placeholder',
forcePlaceholderSize: true,
receive: function(event, ui) {
// Same logic as in initSortable
const row = $(this);

if (ui.item.hasClass('metric-item')) {
    const metricData = {
        id: ui.item.data('id'),
        type: ui.item.data('type'),
        title: ui.item.data('title'),
        value_key: ui.item.data('value-key'),
        position: {
            row: parseInt(row.attr('data-row')),
            col: row.children().length - 1
        }
    };
    
    const newMetric = createDashboardMetric(metricData);
    ui.item.replaceWith(newMetric);
}

if (row.children().length > 4) {
    const lastItem = row.children().last();
    
    let nextRow = row.next('.metrics-row');
    if (!nextRow.length) {
        addMetricsRow();
        nextRow = row.next('.metrics-row');
    }
    
    lastItem.detach();
    nextRow.append(lastItem);
    nextRow.addClass('has-items');
}

updateRowStatus(row);
updateConfiguration();
},
update: function(event, ui) {
updateColumnPositions($(this));
updateConfiguration();
}
});

return newRow;
}

// Function to add a new charts row
function addChartsRow() {
const rowIndex = $('.charts-row').length;
const newRow = $('<div class="charts-row"></div>').attr('data-row', rowIndex);
$('#charts-container').append(newRow);

// Initialize sortable for the new row
newRow.sortable({
tolerance: 'pointer',
connectWith: '.charts-row',
placeholder: 'ui-sortable-placeholder',
forcePlaceholderSize: true,
receive: function(event, ui) {
// Same logic as in initSortable
const row = $(this);

if (ui.item.hasClass('chart-item')) {
    const chartData = {
        id: ui.item.data('id'),
        type: ui.item.data('type'),
        title: ui.item.data('title'),
        data_key: ui.item.data('data-key'),
        position: {
            row: parseInt(row.attr('data-row')),
            col: row.children().length - 1
        },
        config: {}
    };
    
    const newChart = createDashboardChart(chartData);
    ui.item.replaceWith(newChart);
}

if (row.children().length > 2) {
    const lastItem = row.children().last();
    
    let nextRow = row.next('.charts-row');
    if (!nextRow.length) {
        addChartsRow();
        nextRow = row.next('.charts-row');
    }
    
    lastItem.detach();
    nextRow.append(lastItem);
    nextRow.addClass('has-items');
}

updateRowStatus(row);
updateConfiguration();
},
update: function(event, ui) {
updateColumnPositions($(this));
updateConfiguration();
}
});

return newRow;
}

// Improved version of the updateConfiguration and saveConfiguration functions
// This can replace the existing functions in your dashboard_editor.js file

// Function to properly update the configuration based on the current layout
function updateConfiguration() {
    // Build a new configuration object with the required structure
    const config = {
        metrics: [],
        charts: [],
        layout: {
            max_cols: 2,
            title: "AlgoSystem Trading Dashboard"
        }
    };

    // Collect metrics - ensure we handle all attributes properly
    $('.metrics-row').each(function() {
        const rowIndex = parseInt($(this).attr('data-row'));

        $(this).children('.dashboard-metric').each(function() {
            const colIndex = parseInt($(this).attr('data-col') || 0);

            const metric = {
                id: $(this).attr('data-id'),
                type: $(this).attr('data-type'),
                title: $(this).attr('data-title'),
                value_key: $(this).attr('data-value-key'),
                position: {
                    row: rowIndex,
                    col: colIndex
                }
            };

            // Only add well-formed metrics
            if (metric.id && metric.type && metric.title && metric.value_key) {
                config.metrics.push(metric);
            }
        });
    });

    // Collect charts - ensure we handle config properly
    $('.charts-row').each(function() {
        const rowIndex = parseInt($(this).attr('data-row'));

        $(this).children('.dashboard-chart').each(function() {
            const colIndex = parseInt($(this).attr('data-col') || 0);

            const chart = {
                id: $(this).attr('data-id'),
                type: $(this).attr('data-type'),
                title: $(this).attr('data-title'),
                data_key: $(this).attr('data-data-key'),
                position: {
                    row: rowIndex,
                    col: colIndex
                },
                config: {}
            };

            // Parse config if present
            const configStr = $(this).attr('data-config');
            if (configStr) {
                try {
                    chart.config = JSON.parse(configStr);
                } catch (e) {
                    console.error('Error parsing chart config:', e);
                    chart.config = {};
                }
            }

            // Only add well-formed charts
            if (chart.id && chart.type && chart.title && chart.data_key) {
                config.charts.push(chart);
            }
        });
    });

    // Log the configuration to help with debugging
    console.log('Updated configuration:', config);
    
    // Make sure the global currentConfig is updated
    currentConfig = config;
    
    return config;
}

// Function to save the configuration
function saveConfiguration() {
    // Update the configuration first
    updateConfiguration();

    // Make a deep copy of the configuration to avoid reference issues
    const configToSave = JSON.parse(JSON.stringify(currentConfig));
    
    // Validate config before sending
    if (!configToSave.metrics) configToSave.metrics = [];
    if (!configToSave.charts) configToSave.charts = [];
    if (!configToSave.layout) {
        configToSave.layout = {
            max_cols: 2,
            title: "AlgoSystem Trading Dashboard"
        };
    }

    // Display a saving indicator
    const saveBtn = $('#save-config');
    const originalText = saveBtn.text();
    saveBtn.text('Saving...');
    saveBtn.prop('disabled', true);

    // Log what we're about to send
    console.log('Saving configuration:', configToSave);
    console.log('Configuration JSON string:', JSON.stringify(configToSave));

    // Send to the server with proper content type and stringify
    $.ajax({
        url: '/api/config',
        type: 'POST',
        data: JSON.stringify(configToSave),
        contentType: 'application/json',
        dataType: 'json',
        success: function(response) {
            saveBtn.text(originalText);
            saveBtn.prop('disabled', false);
            
            if (response.status === 'success') {
                // Show success message
                const successMessage = `Configuration saved successfully to ${response.path}!`;
                alert(successMessage);
                console.log(successMessage);
                
                // Verify the save by re-fetching the configuration
                $.getJSON('/api/config', function(savedConfig) {
                    console.log('Verification - Configuration on server contains:', savedConfig);
                });
            } else {
                // Show error
                const errorMessage = `Error saving configuration: ${response.message}`;
                alert(errorMessage);
                console.error(errorMessage);
            }
        },
        error: function(xhr, status, error) {
            saveBtn.text(originalText);
            saveBtn.prop('disabled', false);
            
            // Show more detailed error
            let errorMsg = 'Error saving configuration';
            if (xhr.responseJSON && xhr.responseJSON.message) {
                errorMsg += ': ' + xhr.responseJSON.message;
            } else {
                errorMsg += ': ' + error;
            }
            alert(errorMsg);
            console.error('Save error:', xhr, status, error);
            console.error('Response text:', xhr.responseText);
        }
    });
}

// Function to reset to the default configuration
function resetConfiguration() {
if (confirm('Are you sure you want to reset to the default configuration? All changes will be lost.')) {
$.ajax({
url: '/api/reset-config',
type: 'POST',
success: function(response) {
    // Reload the configuration
    $.getJSON('/api/config', function(config) {
        currentConfig = config;
        renderDashboard(config);
    });
    
    alert('Reset to default configuration successfully!');
},
error: function(xhr, status, error) {
    alert('Error resetting configuration: ' + error);
}
});
}
}

// Function to view the dashboard
function viewDashboard() {
// Save the configuration first
saveConfiguration();

// Open the dashboard in a new tab
window.open('/dashboard', '_blank');
}

// Function to upload and process a CSV file
function uploadCSV() {
const fileInput = $('#csv-file')[0];
if (!fileInput.files.length) {
$('#upload-status').text('Please select a file first.');
return;
}

const file = fileInput.files[0];
const formData = new FormData();
formData.append('file', file);

$('#upload-status').text('Uploading and processing file...');

$.ajax({
url: '/api/upload-csv',
type: 'POST',
data: formData,
processData: false,
contentType: false,
success: function(response) {
if (response.status === 'success') {
    $('#upload-status').html(`<span style="color: green;">${response.message}</span>`);
    $('#view-dashboard').prop('disabled', false);
} else {
    $('#upload-status').html(`<span style="color: red;">${response.message}</span>`);
}
},
error: function(xhr, status, error) {
$('#upload-status').html(`<span style="color: red;">Error: ${error}</span>`);
}
});
}

// Function to initialize category toggles
function initCategoryToggles() {
    $('.category-header').click(function() {
        const toggle = $(this).find('.category-toggle');
        const content = $(this).next('.category-content');
        
        // Toggle display
        content.slideToggle(200);
        
        // Update toggle icon
        if (toggle.hasClass('open')) {
            toggle.removeClass('open');
            toggle.text('▶');
        } else {
            toggle.addClass('open');
            toggle.text('▼');
        }
    });
    
    // Open the first category in each section by default
    $('.metric-categories .category-section:first-child .category-header').click();
    $('.chart-categories .category-section:first-child .category-header').click();
}

});
