/**
 * Chart Factory - Functions for creating various chart types
 */

// Store chart instances for later reference
const chartInstances = {};

/**
 * Create a line chart
 * @param {string} containerId - ID of the container element
 * @param {object} data - Chart data
 * @param {object} options - Chart options
 */
function createLineChart(containerId, data, options) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    // Clear existing content
    container.innerHTML = '';
    
    // Create canvas element
    const canvas = document.createElement('canvas');
    container.appendChild(canvas);
    
    // Check if data is available
    if (!data || !data.labels || !data.datasets || data.labels.length === 0) {
        container.innerHTML = '<div class="error-message">No data available</div>';
        return;
    }
    
    // Ensure all datasets have no point dots
    if (data.datasets) {
        data.datasets.forEach(dataset => {
            dataset.pointRadius = 0;
            dataset.pointHoverRadius = 2;
            dataset.pointHitRadius = 10;
        });
    }
    
    // Create chart instance
    chartInstances[containerId] = new Chart(canvas, {
        type: 'line',
        data: data,
        options: options || {}
    });
}

/**
 * Create a heatmap table
 * @param {string} containerId - ID of the container element
 * @param {object} data - Heatmap data
 */
function createHeatmapTable(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    // Clear existing content
    container.innerHTML = '';
    
    // Check if data is available
    if (!data || !data.years || !data.months || data.years.length === 0) {
        container.innerHTML = '<div class="error-message">No data available</div>';
        return;
    }
    
    // Create table element
    const table = document.createElement('table');
    table.className = 'heatmap-table';
    container.appendChild(table);
    
    // Create header row
    const headerRow = document.createElement('tr');
    
    // Add empty corner cell
    const cornerCell = document.createElement('th');
    headerRow.appendChild(cornerCell);
    
    // Add month headers
    for (const month of data.months) {
        const cell = document.createElement('th');
        cell.textContent = month;
        headerRow.appendChild(cell);
    }
    
    table.appendChild(headerRow);
    
    // Create data rows
    for (const year of data.years) {
        const row = document.createElement('tr');
        
        // Add year header
        const yearCell = document.createElement('th');
        yearCell.textContent = year;
        row.appendChild(yearCell);
        
        // Add data cells
        for (let month = 1; month <= 12; month++) {
            const cell = document.createElement('td');
            const key = `${year}-${month}`;
            
            if (key in data.data) {
                const value = data.data[key];
                
                // Format value
                cell.textContent = formatAsPercentage(value);
                
                // Apply color scale
                applyHeatmapColor(cell, value);
            }
            
            row.appendChild(cell);
        }
        
        table.appendChild(row);
    }
}

/**
 * Apply color to heatmap cell based on value
 * @param {HTMLElement} cell - Table cell element
 * @param {number} value - Cell value
 */
function applyHeatmapColor(cell, value) {
    if (value > 0.03) {
        cell.style.backgroundColor = 'rgba(46, 204, 113, 0.8)';
        cell.style.color = 'white';
    } else if (value > 0.01) {
        cell.style.backgroundColor = 'rgba(46, 204, 113, 0.5)';
    } else if (value > 0) {
        cell.style.backgroundColor = 'rgba(46, 204, 113, 0.2)';
    } else if (value > -0.01) {
        cell.style.backgroundColor = 'rgba(231, 76, 60, 0.2)';
    } else if (value > -0.03) {
        cell.style.backgroundColor = 'rgba(231, 76, 60, 0.5)';
    } else {
        cell.style.backgroundColor = 'rgba(231, 76, 60, 0.8)';
        cell.style.color = 'white';
    }
}

/**
 * Format value as percentage
 * @param {number} value - Value to format
 * @returns {string} - Formatted percentage
 */
function formatAsPercentage(value) {
    return `${(value * 100).toFixed(1)}%`;
}

/**
 * Format value
 * @param {number} value - Value to format
 * @returns {string} - Formatted value
 */
function formatValue(value) {
    return value.toFixed(2);
}

/**
 * Format value as currency
 * @param {number} value - Value to format
 * @returns {string} - Formatted currency
 */
function formatAsCurrency(value) {
    return `$${value.toFixed(2)}`;
}