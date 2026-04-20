/**
 * AI Benchmarking UI - JavaScript frontend
 */

let appState = {
    provider: 'gemini',
    customEndpoint: '',
    apiKey: '',
    selectedModel: null,
    availableModels: [],
    selectedTasks: [],
    allTasks: [],
    benchmarkRunning: false
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', async () => {
    await initializeUI();
    setupEventListeners();
});

// Handle page unload/close - stop the benchmark if running
window.addEventListener('beforeunload', async (e) => {
    if (appState.benchmarkRunning) {
        // Try to stop the benchmark on the server
        try {
            await fetch('/api/stop-benchmark', { method: 'POST' });
        } catch (err) {
            console.error('Error stopping benchmark:', err);
        }
        
        // Warn the user
        e.preventDefault();
        e.returnValue = 'Benchmark is still running. Are you sure you want to close?';
        return 'Benchmark is still running. Are you sure you want to close?';
    }
});

/**
 * Initialize UI with data from server
 */
async function initializeUI() {
    try {
        // Load config (including API key from .env)
        const configResponse = await fetch('/api/config');
        const config = await configResponse.json();
        
        if (config.api_key) {
            document.getElementById('apiKey').value = config.api_key;
            appState.apiKey = config.api_key;
        }
        
        // Load available tasks
        const tasksResponse = await fetch('/api/tasks');
        const tasksData = await tasksResponse.json();
        
        if (tasksData.success) {
            appState.allTasks = tasksData.tasks;
            appState.selectedTasks = tasksData.tasks.map(t => t.filename);
            renderTasks();
        }
    } catch (error) {
        console.error('Error initializing UI:', error);
    }
}

/**
 * Setup event listeners
 */
function setupEventListeners() {
    // Provider change
    document.getElementById('provider').addEventListener('change', (e) => {
        appState.provider = e.target.value;
        // Show/hide custom endpoint field based on provider
        const customEndpointGroup = document.getElementById('customEndpointGroup');
        if (e.target.value === 'other') {
            customEndpointGroup.style.display = 'block';
        } else {
            customEndpointGroup.style.display = 'none';
            appState.customEndpoint = '';
            document.getElementById('customEndpoint').value = '';
        }
    });
    
    // Custom Endpoint change
    document.getElementById('customEndpoint').addEventListener('input', (e) => {
        appState.customEndpoint = e.target.value;
    });
    
    // API Key change
    document.getElementById('apiKey').addEventListener('input', (e) => {
        appState.apiKey = e.target.value;
    });
    
    // Test Connection button
    document.getElementById('testConnectionBtn').addEventListener('click', testConnection);
    
    // Select All checkbox
    document.getElementById('selectAllTasks').addEventListener('change', (e) => {
        if (e.target.checked) {
            appState.selectedTasks = appState.allTasks.map(t => t.filename);
            document.getElementById('selectNoneTasks').checked = false;
        } else {
            appState.selectedTasks = [];
            document.getElementById('selectNoneTasks').checked = false;
        }
        renderTasks();
    });
    
    // Select None checkbox
    document.getElementById('selectNoneTasks').addEventListener('change', (e) => {
        if (e.target.checked) {
            appState.selectedTasks = [];
            document.getElementById('selectAllTasks').checked = false;
        }
        renderTasks();
    });
    
    // Run Benchmark button
    document.getElementById('runBenchmarkBtn').addEventListener('click', runBenchmark);
    
    // Stop Benchmark button
    document.getElementById('stopBenchmarkBtn').addEventListener('click', stopBenchmark);
    
    // Download Results button
    document.getElementById('downloadResultsBtn').addEventListener('click', downloadResults);
    
    // Close Application button (top)
    document.getElementById('shutdownBtnTop').addEventListener('click', shutdownServer);
}

/**
 * Render task list organized into sections
 */
function renderTasks() {
    const tasksList = document.getElementById('tasksList');
    tasksList.innerHTML = '';
    
    console.log('[DEBUG] renderTasks: appState.allTasks count:', appState.allTasks.length);
    console.log('[DEBUG] renderTasks: appState.selectedTasks:', appState.selectedTasks);
    
    // Render flat list of tasks
    appState.allTasks.forEach(task => {
        const isSelected = appState.selectedTasks.includes(task.filename);
        console.log(`[DEBUG] Task "${task.name}": filename="${task.filename}", isSelected=${isSelected}`);
        
        const taskItem = document.createElement('div');
        taskItem.className = 'task-item';
        taskItem.innerHTML = `
            <label>
                <input type="checkbox" class="task-checkbox" 
                       data-filename="${task.filename}"
                       ${isSelected ? 'checked' : ''}>
                ${task.name}
            </label>
        `;
        
        taskItem.querySelector('input').addEventListener('change', (e) => {
            if (e.target.checked) {
                if (!appState.selectedTasks.includes(task.filename)) {
                    appState.selectedTasks.push(task.filename);
                }
            } else {
                appState.selectedTasks = appState.selectedTasks.filter(f => f !== task.filename);
            }
            
            // Update Select All/None checkboxes
            updateSelectAllCheckbox();
            updateRunButton();
        });
        
        tasksList.appendChild(taskItem);
    });
    
    updateSelectAllCheckbox();
    updateRunButton();
}

/**
 * Update Select All checkbox state
 */
function updateSelectAllCheckbox() {
    const selectAllCheckbox = document.getElementById('selectAllTasks');
    const selectNoneCheckbox = document.getElementById('selectNoneTasks');
    
    const allSelected = appState.selectedTasks.length === appState.allTasks.length;
    const noneSelected = appState.selectedTasks.length === 0;
    
    selectAllCheckbox.checked = allSelected;
    selectAllCheckbox.indeterminate = !allSelected && appState.selectedTasks.length > 0;
    
    // Check "Select None" when no tasks are selected
    selectNoneCheckbox.checked = noneSelected;
}

/**
 * Update Run Benchmark button enabled state
 */
function updateRunButton() {
    const runBtn = document.getElementById('runBenchmarkBtn');
    const shouldDisable = !appState.selectedModel || appState.selectedTasks.length === 0 || appState.benchmarkRunning;
    runBtn.disabled = shouldDisable;
    console.log('[DEBUG] updateRunButton:', {
        selectedModel: appState.selectedModel,
        selectedTasksCount: appState.selectedTasks.length,
        benchmarkRunning: appState.benchmarkRunning,
        disabled: shouldDisable
    });
}

/**
 * Test connection and detect available models
 */
async function testConnection() {
    const btn = document.getElementById('testConnectionBtn');
    const messageDiv = document.getElementById('connectionMessage');
    
    if (!appState.apiKey) {
        showMessage(messageDiv, 'API key is required', 'error');
        return;
    }
    
    btn.disabled = true;
    btn.innerHTML = '<span class="loading"></span>Testing...';
    messageDiv.innerHTML = '';
    
    try {
        const response = await fetch('/api/test-connection', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                provider: appState.provider,
                api_key: appState.apiKey,
                custom_endpoint: appState.customEndpoint || null
            })
        });
        
        if (!response.ok) {
            throw new Error(`Server returned ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            appState.availableModels = result.models;
            showMessage(messageDiv, result.message, 'success');
            renderModels();
        } else {
            showMessage(messageDiv, result.message, 'error');
        }
    } catch (error) {
        console.error('Test connection error:', error);
        showMessage(messageDiv, `Error: ${error.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = 'Test Connection & Detect Versions';
    }
}

/**
 * Categorize models into logical groups
 */
function categorizeModels(models) {
    const categories = {
        'Text Generation': [],
        'Image Generation': [],
        'Audio': [],
        'Embedding': [],
        'Specialized': []
    };
    
    models.forEach(model => {
        const name = model.replace(/^models\//, '');
        
        if (name.includes('imagen') || name.includes('veo')) {
            categories['Image Generation'].push(model);
        } else if (name.includes('audio') || name.includes('tts')) {
            categories['Audio'].push(model);
        } else if (name.includes('embedding')) {
            categories['Embedding'].push(model);
        } else if (name.includes('aqa') || name.includes('lyria') || name.includes('robotics') || name.includes('deep-research')) {
            categories['Specialized'].push(model);
        } else {
            categories['Text Generation'].push(model);
        }
    });
    
    // Remove empty categories
    Object.keys(categories).forEach(key => {
        if (categories[key].length === 0) {
            delete categories[key];
        }
    });
    
    return categories;
}

/**
 * Render available models as radio buttons organized by category
 */
function renderModels() {
    const modelsContainer = document.getElementById('modelsContainer');
    const modelsList = document.getElementById('modelsList');
    
    if (appState.availableModels.length === 0) {
        modelsContainer.style.display = 'none';
        return;
    }
    
    modelsList.innerHTML = '';
    
    const categories = categorizeModels(appState.availableModels);
    let modelIndex = 0;
    
    Object.keys(categories).forEach(category => {
        // Create category heading
        const categoryHeading = document.createElement('div');
        categoryHeading.className = 'model-category-heading';
        categoryHeading.textContent = category;
        modelsList.appendChild(categoryHeading);
        
        // Create category container
        const categoryContainer = document.createElement('div');
        categoryContainer.className = 'model-category-models';
        
        categories[category].forEach((model, catIndex) => {
            // Strip "models/" prefix for display
            const displayName = model.replace(/^models\//, '');
            
            const modelOption = document.createElement('div');
            modelOption.className = 'model-option';
            modelOption.innerHTML = `
                <input type="radio" name="model" id="model-${modelIndex}" 
                       value="${model}" ${modelIndex === 0 ? 'checked' : ''}>
                <label for="model-${modelIndex}">${displayName}</label>
            `;
            
            modelOption.querySelector('input').addEventListener('change', (e) => {
                if (e.target.checked) {
                    appState.selectedModel = model;
                    updateSelectedModelDisplay();
                    updateRunButton();
                }
            });
            
            categoryContainer.appendChild(modelOption);
            modelIndex++;
        });
        
        modelsList.appendChild(categoryContainer);
    });
    
    modelsContainer.style.display = 'block';
    
    // Select first model by default
    if (appState.availableModels.length > 0) {
        appState.selectedModel = appState.availableModels[0];
        updateSelectedModelDisplay();
        updateRunButton();
    }
}

/**
 * Update selected model display
 */
function updateSelectedModelDisplay() {
    const display = document.getElementById('selectedModelName');
    const modelName = appState.selectedModel ? appState.selectedModel.replace(/^models\//, '') : 'None';
    display.textContent = modelName;
}

/**
 * Run benchmark
 */
async function runBenchmark() {
    const btn = document.getElementById('runBenchmarkBtn');
    const stopBtn = document.getElementById('stopBenchmarkBtn');
    btn.disabled = true;
    
    const evaluationChecked = document.getElementById('runEvaluation').checked;
    console.log(`[DEBUG] runBenchmark - evaluation checkbox is: ${evaluationChecked}`);
    
    try {
        const payload = {
            provider: appState.provider,
            api_key: appState.apiKey,
            custom_endpoint: appState.customEndpoint || null,
            model: appState.selectedModel,
            task_files: appState.selectedTasks,
            run_evaluation: evaluationChecked
        };
        console.log(`[DEBUG] runBenchmark - sending payload:`, payload);
        
        const response = await fetch('/api/run-benchmark', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const result = await response.json();
        
        if (result.success) {
            appState.benchmarkRunning = true;
            stopBtn.style.display = 'inline-block';
            showProgressSection();
            pollBenchmarkStatus();
        } else {
            showErrorMessage(result.message);
        }
    } catch (error) {
        showErrorMessage(`Error: ${error.message}`);
    } finally {
        btn.disabled = true;
    }
}

/**
 * Stop the running benchmark
 */
async function stopBenchmark() {
    console.log('[DEBUG] stopBenchmark called');
    try {
        const response = await fetch('/api/stop-benchmark', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        console.log('[DEBUG] stop-benchmark response:', result);
        
        if (result.success) {
            showInfoMessage('Stop requested. The benchmark will stop after the current question completes.');
            document.getElementById('stopBenchmarkBtn').style.display = 'none';
        } else {
            showErrorMessage(result.message || 'Failed to stop benchmark');
        }
    } catch (error) {
        showErrorMessage(`Error stopping benchmark: ${error.message}`);
    }
}

/**
 * Poll benchmark status
 */
function pollBenchmarkStatus() {
    // Poll more frequently (250ms instead of 500ms) for better responsiveness
    const pollInterval = setInterval(async () => {
        try {
            const response = await fetch('/api/benchmark-status');
            const status = await response.json();
            
            updateProgressDisplay(status);
            
            if (!status.running) {
                clearInterval(pollInterval);
                appState.benchmarkRunning = false;
                document.getElementById('stopBenchmarkBtn').style.display = 'none';
                
                if (status.error) {
                    showErrorMessage(status.error);
                } else {
                    showResultsSection();
                }
                
                document.getElementById('runBenchmarkBtn').disabled = false;
            }
        } catch (error) {
            console.error('Error polling status:', error);
            clearInterval(pollInterval);
            document.getElementById('stopBenchmarkBtn').style.display = 'none';
        }
    }, 250);
}

/**
 * Update progress display
 */
function updateProgressDisplay(status) {
    // Always update progress bar (even if 0)
    const progressPercent = (status.progress / status.total) * 100;
    document.getElementById('progressBarFill').style.width = progressPercent + '%';
    
    document.getElementById('progressCount').textContent = status.progress;
    document.getElementById('totalCount').textContent = status.total;
    
    // Update task group progress elements only if they exist in HTML
    const taskGroupCountEl = document.getElementById('taskGroupCount');
    const taskGroupTotalEl = document.getElementById('taskGroupTotal');
    if (taskGroupCountEl && taskGroupTotalEl && 
        status.task_group_progress !== undefined && status.task_group_total !== undefined) {
        taskGroupCountEl.textContent = status.task_group_progress;
        taskGroupTotalEl.textContent = status.task_group_total;
    }
    
    document.getElementById('progressMessage').textContent = status.message;
    
    const elapsedTime = formatTime(status.elapsed_time);
    document.getElementById('elapsedTimeDisplay').textContent = `Elapsed: ${elapsedTime}`;
}

/**
 * Format time in seconds to HH:MM:SS
 */
function formatTime(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    return [hours, minutes, secs]
        .map(v => String(v).padStart(2, '0'))
        .join(':');
}

/**
 * Show progress section
 */
function showProgressSection() {
    document.getElementById('progressSection').style.display = 'block';
    document.getElementById('resultsSection').style.display = 'none';
    document.getElementById('errorSection').style.display = 'none';
}

/**
 * Show results section
 */
async function showResultsSection() {
    document.getElementById('progressSection').style.display = 'none';
    document.getElementById('resultsSection').style.display = 'block';
    
    const status = await fetch('/api/benchmark-status').then(r => r.json());
    
    if (status.results_file) {
        const finalStats = document.getElementById('finalStats');
        finalStats.innerHTML = `
            <div><span>Status:</span><span>Completed</span></div>
            <div><span>Results File:</span><span>${status.results_file}</span></div>
            <div><span>Elapsed Time:</span><span>${formatTime(status.elapsed_time)}</span></div>
        `;
    }
}

/**
 * Show error message
 */
function showErrorMessage(message) {
    document.getElementById('progressSection').style.display = 'none';
    document.getElementById('resultsSection').style.display = 'none';
    
    const errorSection = document.getElementById('errorSection');
    errorSection.style.display = 'block';
    errorSection.textContent = `✗ Error: ${message}`;
}

/**
 * Show info message (non-blocking)
 */
function showInfoMessage(message) {
    const errorSection = document.getElementById('errorSection');
    errorSection.style.display = 'block';
    errorSection.style.backgroundColor = '#d4edda';
    errorSection.style.color = '#155724';
    errorSection.style.borderColor = '#c3e6cb';
    errorSection.textContent = `ℹ ${message}`;
}

/**
 * Download results
 */
async function downloadResults() {
    try {
        const response = await fetch('/api/download-results');
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = 'benchmark_results.zip';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
        } else {
            const error = await response.json();
            showErrorMessage(error.message);
        }
    } catch (error) {
        showErrorMessage(`Download error: ${error.message}`);
    }
}

/**
 * Show message in message div
 */
function showMessage(messageDiv, message, type) {
    messageDiv.textContent = message;
    messageDiv.className = `message ${type}`;
}

/**
 * Shutdown the Flask server
 */
async function shutdownServer() {
    if (appState.benchmarkRunning) {
        alert('Cannot shutdown while benchmark is running. Stop the benchmark first.');
        return;
    }
    
    if (confirm('Are you sure you want to shutdown the server? The application will close.')) {
        try {
            await fetch('/api/shutdown', {
                method: 'POST'
            });
            
            // Give the server time to shut down
            setTimeout(() => {
                alert('Server shutting down...');
                window.close();
            }, 1000);
        } catch (error) {
            console.error('Error shutting down:', error);
            alert('Error shutting down server: ' + error.message);
        }
    }
}

