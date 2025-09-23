class TaskList extends HTMLElement {
    constructor() {
        super();
        this.baseUrl = this.getAttribute('base_url') || window.location.origin;
        this.activeSSEConnections = new Map();
        this.init();
    }

    init() {
        this.render();
        this.loadTasks();
        this.startQueueSSEConnection();
    }

    render() {
        this.innerHTML = `
            <!-- Bootstrap Tabs -->
            <ul class="nav nav-tabs" id="taskTabs" role="tablist">
                <li class="nav-item" role="presentation">
                    <button class="nav-link active" id="tasks-tab" data-bs-toggle="tab" data-bs-target="#tasks-pane" type="button" role="tab" aria-controls="tasks-pane" aria-selected="true">
                        Tasks
                    </button>
                </li>
                <li class="nav-item" role="presentation">
                    <button class="nav-link" id="recurring-tab" data-bs-toggle="tab" data-bs-target="#recurring-pane" type="button" role="tab" aria-controls="recurring-pane" aria-selected="false">
                        Recurring Tasks
                    </button>
                </li>
            </ul>
            
            <!-- Tab Content -->
            <div class="tab-content" id="taskTabContent">
                <!-- Tasks Tab -->
                <div class="tab-pane fade show active" id="tasks-pane" role="tabpanel" aria-labelledby="tasks-tab">
                    <div class="row mt-3" id="taskGrid">
                        <div class="col-12 d-flex justify-content-center py-4">
                            <div class="spinner-border" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Recurring Tasks Tab -->
                <div class="tab-pane fade" id="recurring-pane" role="tabpanel" aria-labelledby="recurring-tab">
                    <div class="row mt-3" id="recurringTaskGrid">
                        <div class="col-12 d-flex justify-content-center py-4">
                            <div class="spinner-border" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        this.taskGrid = this.querySelector('#taskGrid');
        this.recurringTaskGrid = this.querySelector('#recurringTaskGrid');
        
        // Add event listener for tab changes
        const recurringTab = this.querySelector('#recurring-tab');
        if (recurringTab) {
            recurringTab.addEventListener('shown.bs.tab', () => {
                this.loadRecurringTasks();
            });
        }
    }

    // Helper function to convert percent or progress to a string
    formatPercent(progress) {
        if (typeof progress === 'number') {
            if (progress < 0) {
                return 'Running...';
            }
            return `${progress}%`;
        }
        if (typeof progress === 'string' && progress.endsWith('%')) {
            return progress;
        }
        return '0%';
    }

    // Helper function to generate progress bar HTML
    generateProgressBar(progress) {
        const percent = typeof progress === 'number' ? progress : 0;
        const percentStr = this.formatPercent(percent);
        
        if (percent < 0) {
            // Animated striped progress bar for indeterminate progress
            return `
                <div class="progress">
                    <div class="progress-bar progress-bar-striped progress-bar-animated" 
                         role="progressbar" 
                         aria-valuenow="100" 
                         aria-valuemin="0" 
                         aria-valuemax="100" 
                         style="width: 100%">
                        ${percentStr}
                    </div>
                </div>
            `;
        } else {
            // Regular progress bar for determinate progress
            return `
                <div class="progress">
                    <div class="progress-bar" 
                         role="progressbar"
                         style="width: ${percent}%;" 
                         aria-valuenow="${percent}"
                         aria-valuemin="0" 
                         aria-valuemax="100">
                        ${percentStr}
                    </div>
                </div>
            `;
        }
    }

    // Render a single task card
    renderTaskCard(task) {
        const card = document.createElement('div');
        card.className = 'col-12'; // Full width in Bootstrap grid
        card.id = `task-${task.task_id}`;

        // Card and badge classes
        let cardClass = 'card mb-3';
        let badgeClass = 'secondary';
        if (task.status === 'running') {
            cardClass += ' border-primary';
            badgeClass = 'primary';
        } else if (task.status === 'done') {
            cardClass += ' border-success';
            badgeClass = 'success';
        } else if (task.status === 'failed') {
            cardClass += ' border-danger';
            badgeClass = 'danger';
        } else if (task.status === 'queued') {
            cardClass += ' border-warning';
            badgeClass = 'warning';
        }

        // Progress bar
        const progressBarHtml = this.generateProgressBar(task.progress);

        // Title and body text from heading and body fields
        const title = task.heading || 'No Title';
        const bodyText = task.body || 'No description available';

        // Task type badge
        const taskTypeDisplay = task.task_type;

        // Determine if we should show image cap or full-width content
        if (task.img) {
            // Card with image cap
            card.innerHTML = `
                <div class="${cardClass} task-card" style="width: 100%;">
                    <div class="row g-0 align-items-stretch" style="height: 100%;">
                        <div class="col-md-3 col-4 p-0" style="height: 100%;">
                            <div style="height: 100%; width: 100%; overflow: hidden;">
                                <img src="${task.img}" class="img-fluid h-100 w-100 rounded-0" alt="task image" style="object-fit: cover; min-height: 120px;">
                            </div>
                        </div>
                        <div class="col-md-9 col-8">
                            <div class="card-body">
                                <div class="d-flex align-items-center mb-2">
                                    <div class="flex-grow-1">
                                        <small class="task-id">Task ID: ${task.task_id}</small>
                                    </div>
                                    <span class="badge bg-${badgeClass} me-2">${task.status.toUpperCase()}</span>
                                    <span class="badge bg-secondary">${taskTypeDisplay}</span>
                                    ${task.status === 'done' || task.status === 'failed' ? 
                                        `<button class="btn btn-sm btn-outline-danger ms-2" onclick="document.querySelector('#task-${task.task_id}').deleteTask('${task.task_id}')">
                                            <i class="bi bi-trash"></i>
                                        </button>` : ''
                                    }
                                </div>
                                
                                <h6 class="card-title mb-2">${title}</h6>
                                <p class="card-text small text-muted mb-3">${bodyText}</p>
                                
                                <div class="mb-2">
                                    ${progressBarHtml}
                                </div>
                                
                                <div class="small text-muted">
                                    <div>Started: ${task.started_at ? new Date(task.started_at).toLocaleString() : 'Not started yet'}</div>
                                    <div>Completed: ${task.completed_at ? new Date(task.completed_at).toLocaleString() : 'Not completed yet'}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        } else {
            // Card without image cap - full width content
            card.innerHTML = `
                <div class="${cardClass} task-card" style="width: 100%;">
                    <div class="card-body">
                        <div class="d-flex align-items-center mb-2">
                            <div class="flex-grow-1">
                                <small class="task-id">Task ID: ${task.task_id}</small>
                            </div>
                            <span class="badge bg-${badgeClass} me-2">${task.status.toUpperCase()}</span>
                            <span class="badge bg-secondary">${taskTypeDisplay}</span>
                            ${task.status === 'done' || task.status === 'failed' ? 
                                `<button class="btn btn-sm btn-outline-danger ms-2" onclick="document.querySelector('#task-${task.task_id}').deleteTask('${task.task_id}')">
                                    <i class="bi bi-trash"></i>
                                </button>` : ''
                            }
                        </div>
                        
                        <h6 class="card-title mb-2">${title}</h6>
                        <p class="card-text small text-muted mb-3">${bodyText}</p>
                        
                        <div class="mb-2">
                            ${progressBarHtml}
                        </div>
                        
                        <div class="small text-muted">
                            <div>Started: ${task.started_at ? new Date(task.started_at).toLocaleString() : 'Not started yet'}</div>
                            <div>Completed: ${task.completed_at ? new Date(task.completed_at).toLocaleString() : 'Not completed yet'}</div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // Add deleteTask method to the card element
        card.deleteTask = (taskId) => {
            this.deleteTask(taskId);
        };
        
        return card;
    }

    // Update an existing card with new task data
    updateTaskCard(task) {
        console.log('Updating task card with data:', task);
        const card = this.querySelector(`#task-${task.task_id}`);
        if (!card) return;
        // Re-render the card body (simplest way)
        const newCard = this.renderTaskCard(task);
        card.replaceWith(newCard);
    }

    // Start SSE connection for a task
    startSSEConnection(task) {
        // Close any existing connection
        if (this.activeSSEConnections.has(task.task_id)) {
            this.activeSSEConnections.get(task.task_id).close();
            this.activeSSEConnections.delete(task.task_id);
        }
        const url = `${this.baseUrl}/${task.task_id}/stream`;
        const eventSource = new EventSource(url, { withCredentials: true });
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log(`SSE message for task ${task.task_id}:`, data);
            this.updateTaskCard(data);
            // Close SSE if task is done/failed AND we have the completed timestamp
            if ((data.status === "done" || data.status === "failed") && 
                (data.status === "failed" || data.completed_at)) {
                console.log(`Closing SSE connection for task ${task.task_id} - status: ${data.status}, completed_at: ${data.completed_at}`);
                eventSource.close();
                this.activeSSEConnections.delete(task.task_id);
            } else if (data.status === "done" || data.status === "failed") {
                console.log(`Task ${task.task_id} is done/failed but no completed_at yet - keeping connection open`);
            }
        };
        eventSource.onerror = (err) => {
            console.error(`SSE error for task ${task.task_id}:`, err);
            eventSource.close();
            this.activeSSEConnections.delete(task.task_id);
        };
        this.activeSSEConnections.set(task.task_id, eventSource);
    }

    // Load all tasks and render them
    async loadTasks() {
        this.taskGrid.innerHTML = `
            <div class="col-12 d-flex justify-content-center py-4">
                <div class="spinner-border" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `;
        try {
            const response = await fetch(`${this.baseUrl}/queue`);
            const tasks = await response.json();
            this.taskGrid.innerHTML = '';
            if (tasks.length === 0) {
                this.taskGrid.innerHTML = '<div class="col-12"><p class="text-muted">No tasks found</p></div>';
                return;
            }
            // Reverse the order to show newest tasks first
            const reversedTasks = tasks.reverse();
            for (const task of reversedTasks) {
                const card = this.renderTaskCard(task);
                this.taskGrid.appendChild(card);
                this.startSSEConnection(task);
            }
        } catch (err) {
            console.error('Error loading tasks:', err);
            this.taskGrid.innerHTML = '<div class="col-12"><p class="text-danger">Error loading tasks</p></div>';
        }
    }

    // Start SSE connection for queue updates
    startQueueSSEConnection() {
        const url = `${this.baseUrl}/queue/stream`;
        this.queueEventSource = new EventSource(url, { withCredentials: true });
        
        this.queueEventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleQueueUpdate(data);
        };
        
        this.queueEventSource.onerror = (err) => {
            console.error('Queue SSE error:', err);
            // Attempt to reconnect after a delay
            setTimeout(() => {
                if (this.queueEventSource.readyState === EventSource.CLOSED) {
                    this.startQueueSSEConnection();
                }
            }, 5000);
        };
    }

    // Handle queue updates (new tasks, removed tasks, etc.)
    handleQueueUpdate(data) {
        if (data.type === 'task_added') {
            // New task added to queue
            const task = data.task;
            
            // Clear "No tasks found" message if it exists
            this.updateNoTasksMessage();
            
            const card = this.renderTaskCard(task);
            // Prepend new task at the top to show newest first
            this.taskGrid.insertBefore(card, this.taskGrid.firstChild);
            this.startSSEConnection(task);
        } else if (data.type === 'task_removed') {
            // Task removed from queue (completed, failed, etc.)
            const taskId = data.task_id;
            const card = this.querySelector(`#task-${taskId}`);
            if (card) {
                card.remove();
                // Close the task's SSE connection if it exists
                if (this.activeSSEConnections.has(taskId)) {
                    this.activeSSEConnections.get(taskId).close();
                    this.activeSSEConnections.delete(taskId);
                }
            }
            
            // Update "No tasks found" message if needed
            this.updateNoTasksMessage();
        } else if (data.type === 'queue_updated') {
            // Full queue update - refresh the entire list
            this.loadTasks();
        }
    }

    // Helper method to update "No tasks found" message
    updateNoTasksMessage() {
        const hasTasks = this.taskGrid.children.length > 0;
        const noTasksMessage = this.querySelector('.text-muted');
        
        if (!hasTasks && !noTasksMessage) {
            // No tasks and no message - add the message
            this.taskGrid.innerHTML = '<div class="col-12"><p class="text-muted">No tasks found</p></div>';
        } else if (hasTasks && noTasksMessage && noTasksMessage.textContent === 'No tasks found') {
            // Has tasks but still showing "No tasks found" - remove the message
            noTasksMessage.remove();
        }
    }

    // Public method to refresh tasks
    refresh() {
        this.loadTasks();
    }

    // Delete a task by ID
    async deleteTask(taskId) {
        try {
            const response = await fetch(`${this.baseUrl}/${taskId}`, {
                method: 'DELETE',
            });
            
            if (response.ok) {
                // Task deleted successfully - remove from display
                const card = this.querySelector(`#task-${taskId}`);
                if (card) {
                    card.remove();
                    // Close the task's SSE connection if it exists
                    if (this.activeSSEConnections.has(taskId)) {
                        this.activeSSEConnections.get(taskId).close();
                        this.activeSSEConnections.delete(taskId);
                    }
                    // Update "No tasks found" message if needed
                    this.updateNoTasksMessage();
                }
            } else {
                console.error('Failed to delete task:', response.statusText);
                alert('Failed to delete task. Please try again.');
            }
        } catch (err) {
            console.error('Error deleting task:', err);
            alert('Error deleting task. Please try again.');
        }
    }

    // Load recurring tasks
    async loadRecurringTasks() {
        this.recurringTaskGrid.innerHTML = `
            <div class="col-12 d-flex justify-content-center py-4">
                <div class="spinner-border" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `;
        
        try {
            const response = await fetch(`${this.baseUrl}/recurring`);
            const recurringTasks = await response.json();
            this.recurringTaskGrid.innerHTML = '';
            
            if (recurringTasks.length === 0) {
                this.recurringTaskGrid.innerHTML = '<div class="col-12"><p class="text-muted">No recurring tasks found</p></div>';
                return;
            }
            
            for (const recurringTask of recurringTasks) {
                const card = this.renderRecurringTaskCard(recurringTask);
                this.recurringTaskGrid.appendChild(card);
            }
        } catch (err) {
            console.error('Error loading recurring tasks:', err);
            this.recurringTaskGrid.innerHTML = '<div class="col-12"><p class="text-danger">Error loading recurring tasks</p></div>';
        }
    }

    // Render a single recurring task card
    renderRecurringTaskCard(recurringTask) {
        const card = document.createElement('div');
        card.className = 'col-12';
        card.id = `recurring-task-${recurringTask.recurring_id}`;

        // Card and badge classes
        let cardClass = 'card mb-3';
        let badgeClass = 'secondary';
        if (recurringTask.enabled) {
            cardClass += ' border-success';
            badgeClass = 'success';
        } else {
            cardClass += ' border-secondary';
            badgeClass = 'secondary';
        }

        // Format dates
        const nextRun = recurringTask.next_run ? new Date(recurringTask.next_run).toLocaleString() : 'Not scheduled';
        const lastRun = recurringTask.last_run ? new Date(recurringTask.last_run).toLocaleString() : 'Never run';
        const created = new Date(recurringTask.created_at).toLocaleString();

        card.innerHTML = `
            <div class="${cardClass} recurring-task-card" style="width: 100%;">
                <div class="card-body">
                    <div class="d-flex align-items-center mb-2">
                        <div class="flex-grow-1">
                            <small class="recurring-task-id">Recurring ID: ${recurringTask.recurring_id}</small>
                        </div>
                        <span class="badge bg-${badgeClass} me-2">${recurringTask.enabled ? 'ENABLED' : 'DISABLED'}</span>
                        <span class="badge bg-secondary">${recurringTask.task_type}</span>
                    </div>
                    
                    <h6 class="card-title mb-2">${recurringTask.task_type} - ${recurringTask.cron_expression}</h6>
                    
                    <div class="row mb-3">
                        <div class="col-md-6">
                            <div class="small text-muted">
                                <div><strong>Next Run:</strong> ${nextRun}</div>
                                <div><strong>Last Run:</strong> ${lastRun}</div>
                                <div><strong>Created:</strong> ${created}</div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="small text-muted">
                                <div><strong>Max Concurrent:</strong> ${recurringTask.max_concurrent}</div>
                                <div><strong>Total Runs:</strong> ${recurringTask.total_runs}</div>
                                <div><strong>Total Failures:</strong> ${recurringTask.total_failures}</div>
                            </div>
                        </div>
                    </div>
                    
                    <div class="d-flex align-items-center">
                        <div class="form-check form-switch me-3">
                            <input class="form-check-input" type="checkbox" id="toggle-${recurringTask.recurring_id}" 
                                   ${recurringTask.enabled ? 'checked' : ''} 
                                   onchange="document.querySelector('#recurring-task-${recurringTask.recurring_id}').toggleRecurringTask('${recurringTask.recurring_id}', this.checked)">
                            <label class="form-check-label" for="toggle-${recurringTask.recurring_id}">
                                ${recurringTask.enabled ? 'Enabled' : 'Disabled'}
                            </label>
                        </div>
                        <button class="btn btn-sm btn-outline-primary" onclick="document.querySelector('#recurring-task-${recurringTask.recurring_id}').refreshRecurringTask()">
                            <i class="bi bi-arrow-clockwise"></i> Refresh
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Add methods to the card element
        card.toggleRecurringTask = (recurringId, enabled) => {
            this.toggleRecurringTask(recurringId, enabled);
        };
        
        card.refreshRecurringTask = () => {
            this.loadRecurringTasks();
        };
        
        return card;
    }

    // Toggle recurring task enabled/disabled
    async toggleRecurringTask(recurringId, enabled) {
        try {
            const endpoint = enabled ? 'enable' : 'disable';
            const response = await fetch(`${this.baseUrl}/recurring/${recurringId}/${endpoint}`, {
                method: 'PATCH',
            });
            
            if (response.ok) {
                // Update the card to reflect the new state
                const card = this.querySelector(`#recurring-task-${recurringId}`);
                if (card) {
                    const badge = card.querySelector('.badge');
                    const label = card.querySelector('.form-check-label');
                    
                    if (enabled) {
                        badge.className = 'badge bg-success me-2';
                        badge.textContent = 'ENABLED';
                        card.className = card.className.replace('border-secondary', 'border-success');
                    } else {
                        badge.className = 'badge bg-secondary me-2';
                        badge.textContent = 'DISABLED';
                        card.className = card.className.replace('border-success', 'border-secondary');
                    }
                    
                    label.textContent = enabled ? 'Enabled' : 'Disabled';
                }
            } else {
                console.error('Failed to toggle recurring task:', response.statusText);
                alert('Failed to toggle recurring task. Please try again.');
                // Revert the toggle switch
                const toggle = this.querySelector(`#toggle-${recurringId}`);
                if (toggle) {
                    toggle.checked = !enabled;
                }
            }
        } catch (err) {
            console.error('Error toggling recurring task:', err);
            alert('Error toggling recurring task. Please try again.');
            // Revert the toggle switch
            const toggle = this.querySelector(`#toggle-${recurringId}`);
            if (toggle) {
                toggle.checked = !enabled;
            }
        }
    }

    // Cleanup method
    disconnectedCallback() {
        // Close all SSE connections when component is removed
        for (const connection of this.activeSSEConnections.values()) {
            connection.close();
        }
        this.activeSSEConnections.clear();
        
        // Close queue SSE connection
        if (this.queueEventSource) {
            this.queueEventSource.close();
        }
    }
}

// Register the custom element
customElements.define('task-list', TaskList);
