// Main JavaScript file for Student Attendance Management System

document.addEventListener('DOMContentLoaded', function() {
    // Add current year to footer
    const footerYear = document.querySelector('.footer .text-muted');
    if (footerYear) {
        const currentYear = new Date().getFullYear();
        footerYear.textContent = footerYear.textContent.replace('{{ now.year }}', currentYear);
    }

    // Auto-hide flash messages after 5 seconds
    const flashMessages = document.querySelectorAll('.alert:not(.alert-permanent)');
    flashMessages.forEach(function(message) {
        setTimeout(function() {
            message.style.transition = 'opacity 1s';
            message.style.opacity = '0';
            setTimeout(function() {
                message.remove();
            }, 1000);
        }, 5000);
    });

    // Confirm delete actions
    const deleteButtons = document.querySelectorAll('[data-confirm]');
    deleteButtons.forEach(function(button) {
        button.addEventListener('click', function(e) {
            if (!confirm(this.dataset.confirm)) {
                e.preventDefault();
            }
        });
    });

    // Disable animated counter for dashboard metrics
    const counterElements = document.querySelectorAll('.counter-number');
    counterElements.forEach(function(counter) {
        // Instead of animating, just set the final value immediately
        if (counter.dataset.count) {
            counter.textContent = counter.dataset.count;
        }
    });

    // Add fade-in animation to main content
    const mainContent = document.querySelector('.container');
    if (mainContent) {
        mainContent.classList.add('fade-in');
    }

    // Add active class to current nav item
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');

    navLinks.forEach(function(link) {
        const linkPath = link.getAttribute('href');
        if (linkPath && currentPath === linkPath) {
            link.classList.add('active');
        }
    });

    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // Make tables sortable if needed
    const sortableTables = document.querySelectorAll('.table-sortable');
    sortableTables.forEach(function(table) {
        const headers = table.querySelectorAll('th');
        headers.forEach(function(header, index) {
            if (!header.classList.contains('no-sort')) {
                header.style.cursor = 'pointer';
                header.addEventListener('click', function() {
                    sortTable(table, index);
                });
            }
        });
    });

    // Function to sort tables
    function sortTable(table, column) {
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const headers = table.querySelectorAll('th');

        // Determine sort direction
        const currentDirection = headers[column].getAttribute('data-sort-direction') || 'asc';
        const newDirection = currentDirection === 'asc' ? 'desc' : 'asc';

        // Reset all headers
        headers.forEach(function(header) {
            header.removeAttribute('data-sort-direction');
            header.classList.remove('sort-asc', 'sort-desc');
        });

        // Set new direction
        headers[column].setAttribute('data-sort-direction', newDirection);
        headers[column].classList.add(newDirection === 'asc' ? 'sort-asc' : 'sort-desc');

        // Sort rows
        rows.sort(function(a, b) {
            const cellA = a.querySelectorAll('td')[column].textContent.trim();
            const cellB = b.querySelectorAll('td')[column].textContent.trim();

            // Check if the content is a date
            const dateA = new Date(cellA);
            const dateB = new Date(cellB);

            if (!isNaN(dateA) && !isNaN(dateB)) {
                return newDirection === 'asc' ? dateA - dateB : dateB - dateA;
            }

            // Check if the content is a number
            const numA = parseFloat(cellA);
            const numB = parseFloat(cellB);

            if (!isNaN(numA) && !isNaN(numB)) {
                return newDirection === 'asc' ? numA - numB : numB - numA;
            }

            // Default to string comparison
            return newDirection === 'asc'
                ? cellA.localeCompare(cellB)
                : cellB.localeCompare(cellA);
        });

        // Reorder rows
        rows.forEach(function(row) {
            tbody.appendChild(row);
        });
    }

    // Image preview for upload forms
    const imageInputs = document.querySelectorAll('input[type="file"][accept*="image"]');
    imageInputs.forEach(function(input) {
        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                // Check if the preview container already exists
                let previewContainer = document.getElementById('image-preview-container');

                // If not, create it
                if (!previewContainer) {
                    previewContainer = document.createElement('div');
                    previewContainer.id = 'image-preview-container';
                    previewContainer.className = 'mt-3 text-center border rounded p-3';
                    this.parentNode.appendChild(previewContainer);
                }

                // Clear previous preview
                previewContainer.innerHTML = '';

                // Create heading
                const heading = document.createElement('h6');
                heading.className = 'mb-2';
                heading.innerHTML = '<i class="fas fa-eye me-1"></i> Image Preview';
                previewContainer.appendChild(heading);

                // Create image element
                const img = document.createElement('img');
                img.className = 'img-fluid img-thumbnail';
                img.style.maxHeight = '200px';

                // Set image source
                const reader = new FileReader();
                reader.onload = function(e) {
                    img.src = e.target.result;
                }
                reader.readAsDataURL(file);

                previewContainer.appendChild(img);
            }
        });
    });
});
