/**
 * Metric Factory - Functions for updating various metric types
 */

/**
 * Update a percentage metric
 * @param {string} metricId - ID of the metric element
 * @param {number} value - Metric value
 */
function updatePercentageMetric(metricId, value) {
    const element = document.getElementById(metricId);
    if (!element) return;
    
    // Format value
    const formattedValue = formatAsPercentage(value);
    
    // Determine class based on value
    const className = value >= 0 ? 'positive' : 'negative';
    
    // Update element
    element.innerHTML = `<span class="${className}">${formattedValue}</span>`;
}

/**
 * Update a value metric
 * @param {string} metricId - ID of the metric element
 * @param {number} value - Metric value
 */
function updateValueMetric(metricId, value) {
    const element = document.getElementById(metricId);
    if (!element) return;
    
    // Format value
    const formattedValue = formatValue(value);
    
    // Determine class based on value
    const className = value >= 0 ? 'positive' : 'negative';
    
    // Update element
    element.innerHTML = `<span class="${className}">${formattedValue}</span>`;
}

/**
 * Update a currency metric
 * @param {string} metricId - ID of the metric element
 * @param {number} value - Metric value
 */
function updateCurrencyMetric(metricId, value) {
    const element = document.getElementById(metricId);
    if (!element) return;
    
    // Format value
    const formattedValue = formatAsCurrency(value);
    
    // Determine class based on value
    const className = value >= 0 ? 'positive' : 'negative';
    
    // Update element
    element.innerHTML = `<span class="${className}">${formattedValue}</span>`;
}