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
    }

    render() {
        this.innerHTML = `
            <div class="row" id="taskGrid">
                <div class="col-12 d-flex justify-content-center py-4">
                    <div class="spinner-border" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
            </div>
        `;
        
        this.taskGrid = this.querySelector('#taskGrid');
    }

    // Helper function to convert percent or progress to a string
    formatPercent(progress) {
        if (typeof progress === 'number') {
            return `${progress}%`;
        }
        if (typeof progress === 'string' && progress.endsWith('%')) {
            return progress;
        }
        return '0%';
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
        } else if (task.status === 'pending') {
            cardClass += ' border-warning';
            badgeClass = 'warning';
        }

        // Progress bar
        const percent = typeof task.progress === 'number' ? task.progress : 0;
        const percentStr = this.formatPercent(percent);

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
                                    <span class="badge bg-info">${taskTypeDisplay}</span>
                                </div>
                                
                                <h6 class="card-title mb-2">${title}</h6>
                                <p class="card-text small text-muted mb-3">${bodyText}</p>
                                
                                <div class="mb-2">
                                    <div class="progress">
                                        <div class="progress-bar" role="progressbar"
                                             style="width: ${percent}%;" aria-valuenow="${percent}"
                                             aria-valuemin="0" aria-valuemax="100">
                                            ${percentStr}
                                        </div>
                                    </div>
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
                            <span class="badge bg-info">${taskTypeDisplay}</span>
                        </div>
                        
                        <h6 class="card-title mb-2">${title}</h6>
                        <p class="card-text small text-muted mb-3">${bodyText}</p>
                        
                        <div class="mb-2">
                            <div class="progress">
                                <div class="progress-bar" role="progressbar"
                                     style="width: ${percent}%;" aria-valuenow="${percent}"
                                     aria-valuemin="0" aria-valuemax="100">
                                    ${percentStr}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        return card;
    }

    // Update an existing card with new task data
    updateTaskCard(task) {
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
        const url = `${this.baseUrl}/api/tasks/${task.task_id}/stream`;
        const eventSource = new EventSource(url, { withCredentials: true });
        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.updateTaskCard(data);
            // Close SSE if task is done or failed
            if (data.status === "done" || data.status === "failed") {
                eventSource.close();
                this.activeSSEConnections.delete(task.task_id);
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
            const response = await fetch(`${this.baseUrl}/api/tasks/queue`);
            const tasks = await response.json();
            this.taskGrid.innerHTML = '';
            if (tasks.length === 0) {
                this.taskGrid.innerHTML = '<div class="col-12"><p class="text-muted">No tasks found</p></div>';
                return;
            }
            for (const task of tasks) {
                const card = this.renderTaskCard(task);
                this.taskGrid.appendChild(card);
                this.startSSEConnection(task);
            }
        } catch (err) {
            console.error('Error loading tasks:', err);
            this.taskGrid.innerHTML = '<div class="col-12"><p class="text-danger">Error loading tasks</p></div>';
        }
    }

    // Public method to refresh tasks
    refresh() {
        this.loadTasks();
    }

    // Cleanup method
    disconnectedCallback() {
        // Close all SSE connections when component is removed
        for (const connection of this.activeSSEConnections.values()) {
            connection.close();
        }
        this.activeSSEConnections.clear();
    }
}

// Register the custom element
customElements.define('task-list', TaskList);
