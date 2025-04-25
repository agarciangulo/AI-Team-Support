// Main JavaScript for Task Manager

$(document).ready(function() {
    // Form submission handler
    $('#updateForm').on('submit', function(e) {
        e.preventDefault();
        
        const updateText = $('#updateText').val().trim();
        if (!updateText) {
            alert('Please enter your update text');
            return;
        }
        
        // Show loading indicator
        $('#submitBtn').prop('disabled', true);
        $('#loadingIndicator').show();
        $('#results').html('<p>Processing your update...</p>');
        
        // Send AJAX request
        $.ajax({
            url: '/api/process_update',
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                update_text: updateText
            }),
            dataType: 'json',
            success: function(response) {
                if (response.success) {
                    displayResults(response);
                } else {
                    $('#results').html(`<div class="alert alert-danger">${response.message}</div>`);
                }
            },
            error: function(xhr, status, error) {
                $('#results').html(`
                    <div class="alert alert-danger">
                        <strong>Error:</strong> Could not process your update. Please try again later.
                    </div>
                `);
                console.error('Error:', error);
            },
            complete: function() {
                // Hide loading indicator
                $('#submitBtn').prop('disabled', false);
                $('#loadingIndicator').hide();
                
                // Refresh categories dropdown
                refreshCategories();
            }
        });
    });
    
    // Check for overdue tasks
    $('#reminderBtn').on('click', function() {
        $(this).prop('disabled', true);
        $('#reminderOutput').html('<p>Checking for overdue tasks...</p>');
        
        $.ajax({
            url: '/api/stale_tasks',
            type: 'GET',
            success: function(response) {
                if (response.success) {
                    if (response.has_stale) {
                        displayStaleTasks(response.tasks_by_employee);
                    } else {
                        $('#reminderOutput').html(`
                            <div class="alert alert-success">${response.message}</div>
                        `);
                    }
                } else {
                    $('#reminderOutput').html(`
                        <div class="alert alert-danger">${response.message}</div>
                    `);
                }
            },
            error: function(xhr, status, error) {
                $('#reminderOutput').html(`
                    <div class="alert alert-danger">
                        <strong>Error:</strong> Could not fetch overdue tasks. Please try again later.
                    </div>
                `);
                console.error('Error:', error);
            },
            complete: function() {
                $('#reminderBtn').prop('disabled', false);
            }
        });
    });
    
    // View tasks by category
    $('#categoryBtn').on('click', function() {
        const category = $('#categoryDropdown').val();
        if (!category) {
            alert('Please select a category');
            return;
        }
        
        $(this).prop('disabled', true);
        $('#categoryResult').html('<p>Fetching tasks...</p>');
        
        $.ajax({
            url: `/api/tasks_by_category?category=${encodeURIComponent(category)}`,
            type: 'GET',
            success: function(response) {
                if (response.success) {
                    if (response.has_tasks) {
                        displayCategoryTasks(response, category);
                    } else {
                        $('#categoryResult').html(`
                            <div class="alert alert-info">${response.message}</div>
                        `);
                    }
                } else {
                    $('#categoryResult').html(`
                        <div class="alert alert-danger">${response.message}</div>
                    `);
                }
            },
            error: function(xhr, status, error) {
                $('#categoryResult').html(`
                    <div class="alert alert-danger">
                        <strong>Error:</strong> Could not fetch tasks. Please try again later.
                    </div>
                `);
                console.error('Error:', error);
            },
            complete: function() {
                $('#categoryBtn').prop('disabled', false);
            }
        });
    });
    
    // Function to refresh categories
    function refreshCategories() {
        $.ajax({
            url: '/api/categories',
            type: 'GET',
            success: function(response) {
                if (response.success) {
                    const dropdown = $('#categoryDropdown');
                    dropdown.empty();
                    
                    response.categories.forEach(function(category) {
                        dropdown.append(`<option value="${category}">${category}</option>`);
                    });
                }
            },
            error: function(xhr, status, error) {
                console.error('Error refreshing categories:', error);
            }
        });
    }
    
    // Function to display task processing results
    function displayResults(response) {
        let html = '<div class="mb-4">';
        
        // Display extracted tasks
        if (response.tasks && response.tasks.length > 0) {
            html += '<h5>Extracted Tasks:</h5>';
            html += '<ul class="task-list">';
            
            response.tasks.forEach(function(task) {
                const statusClass = getStatusClass(task.status);
                html += `
                    <li class="task-item">
                        ${task.task}
                        <span class="task-status ${statusClass}">${task.status}</span>
                    </li>
                `;
            });
            
            html += '</ul>';
            html += `<div class="alert alert-success">✅ ${response.tasks.length} tasks synced to Notion.</div>`;
        }
        
        // Display coaching insights
        if (response.coaching) {
            html += `
                <div class="insights-section">
                    <h5>Assessment of Your Recent Work:</h5>
                    <p>${response.coaching}</p>
                </div>
            `;
        }
        
        // Display logs if in debug mode
        if (response.logs && response.logs.length > 0) {
            html += `
                <details class="mt-3">
                    <summary>Technical Details (click to expand)</summary>
                    <div class="tech-details">
                        ${response.logs.join('<br>')}
                    </div>
                </details>
            `;
        }
        
        html += '</div>';
        $('#results').html(html);
    }
    
    // Function to display stale tasks
    function displayStaleTasks(tasksByEmployee) {
        let html = '<h5>Overdue Tasks:</h5>';
        
        for (const employee in tasksByEmployee) {
            html += `
                <div class="employee-section">
                    <div class="employee-name">👤 ${employee}</div>
                    <ul class="task-list">
            `;
            
            tasksByEmployee[employee].forEach(function(task) {
                const statusClass = getStatusClass(task.status);
                html += `
                    <li class="task-item">
                        ${task.task}
                        <span class="task-status ${statusClass}">${task.status}</span>
                        <br>
                        <small class="text-muted">Since ${task.date} (${task.days_old} days)</small>
                    </li>
                `;
            });
            
            html += `
                    </ul>
                </div>
            `;
        }
        
        $('#reminderOutput').html(html);
    }
    
    // Function to display category tasks
    function displayCategoryTasks(response, category) {
        let html = `<h5>Tasks for "${category}":</h5>`;
        
        // Display tasks by employee
        const tasksByEmployee = response.tasks_by_employee;
        for (const employee in tasksByEmployee) {
            html += `
                <div class="employee-section">
                    <div class="employee-name">👤 ${employee}</div>
                    <ul class="task-list">
            `;
            
            tasksByEmployee[employee].forEach(function(task) {
                const statusClass = getStatusClass(task.status);
                html += `
                    <li class="task-item">
                        ${task.task}
                        <span class="task-status ${statusClass}">${task.status}</span>
                        <br>
                        <small class="text-muted">Date: ${task.date}</small>
                    </li>
                `;
            });
            
            html += `
                    </ul>
                </div>
            `;
        }
        
        // Display status summary
        if (response.status_summary) {
            html += '<div class="mt-3">';
            html += `<h6>📊 Project "${category}" Task Status Summary:</h6>`;
            html += '<ul>';
            
            for (const status in response.status_summary) {
                html += `<li>${status}: ${response.status_summary[status]} task(s)</li>`;
            }
            
            html += '</ul>';
            html += '</div>';
        }
        
        // Display AI insight
        if (response.insight) {
            html += `
                <div class="insights-section mt-3">
                    <h6>🧠 AI Project Insight:</h6>
                    <p>${response.insight}</p>
                </div>
            `;
        }
        
        $('#categoryResult').html(html);
    }
    
    // Helper function to get status class
    function getStatusClass(status) {
        switch (status.toLowerCase()) {
            case 'completed':
                return 'status-completed';
            case 'in progress':
                return 'status-in-progress';
            case 'pending':
                return 'status-pending';
            case 'blocked':
                return 'status-blocked';
            default:
                return '';
        }
    }
});