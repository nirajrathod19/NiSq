document.addEventListener('DOMContentLoaded', function() {
    // Initialize file upload functionality
    initFileUpload();
    
    // Mark current page as active in nav
    markActiveNavLink();
    
    // Enable buttons when files are selected
    enableButtonsOnFileSelection();
});

// Mark the active navigation link based on current URL
function markActiveNavLink() {
    const currentPath = window.location.pathname;
    
    // For desktop navigation
    const desktopLinks = document.querySelectorAll('.desktop-nav .nav-link');
    desktopLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
    
    // For mobile navigation
    const mobileLinks = document.querySelectorAll('.mobile-menu-link');
    mobileLinks.forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
    
    // For semi-circular menu
    const menuItems = document.querySelectorAll('.menu-item');
    menuItems.forEach(item => {
        if (item.getAttribute('href') === currentPath) {
            item.classList.add('active');
        }
    });
}

// Initialize file upload areas with drag and drop functionality
function initFileUpload() {
    const uploadAreas = document.querySelectorAll('.upload-area');
    
    uploadAreas.forEach(area => {
        const input = area.querySelector('input[type="file"]');
        
        if (!input) return;
        
        // Highlight drop area when item is dragged over it
        area.addEventListener('dragover', function(e) {
            e.preventDefault();
            area.classList.add('highlight');
        });
        
        area.addEventListener('dragleave', function() {
            area.classList.remove('highlight');
        });
        
        area.addEventListener('drop', function(e) {
            e.preventDefault();
            area.classList.remove('highlight');
            
            // Handle the dropped files
            if (e.dataTransfer.files.length) {
                input.files = e.dataTransfer.files;
                triggerChangeEvent(input);
            }
        });
        
        // Handle click to browse files
        area.addEventListener('click', function() {
            input.click();
        });
        
        // Stop propagation from input to prevent double click
        input.addEventListener('click', function(e) {
            e.stopPropagation();
        });
        
        // Handle file selection change
        input.addEventListener('change', function() {
            if (this.files.length) {
                updateFileSelectionUI(area, this.files);
            }
        });
    });
}

// Enable submit buttons when files are selected
function enableButtonsOnFileSelection() {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            const form = this.closest('form');
            if (form) {
                const submitBtn = form.querySelector('button[type="submit"]');
                if (submitBtn) {
                    submitBtn.disabled = !this.files.length;
                }
            }
        });
    });
}

// Update UI to reflect selected files
function updateFileSelectionUI(area, files) {
    const uploadText = area.querySelector('.upload-text');
    if (uploadText) {
        if (files.length === 1) {
            uploadText.textContent = `Selected: ${files[0].name} (${formatFileSize(files[0].size)})`;
        } else {
            uploadText.textContent = `Selected: ${files.length} files`;
        }
    }
    
    // Enable the submit button
    const form = area.closest('form');
    if (form) {
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = false;
        }
    }
}

// Trigger a change event on an element
function triggerChangeEvent(element) {
    const event = new Event('change', { bubbles: true });
    element.dispatchEvent(event);
}

// Format file size in human-readable format
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Display multiple file selections for photo-to-pdf
function initMultiFileDisplay() {
    const multiFileInput = document.getElementById('multiFileInput');
    const selectedFilesList = document.getElementById('selectedFiles');
    
    if (multiFileInput && selectedFilesList) {
        multiFileInput.addEventListener('change', function() {
            // Clear the list
            selectedFilesList.innerHTML = '';
            
            if (this.files.length === 0) {
                selectedFilesList.innerHTML = '<li class="list-group-item">No files selected</li>';
                return;
            }
            
            // Add each file to the list
            for (let i = 0; i < this.files.length; i++) {
                const file = this.files[i];
                const listItem = document.createElement('li');
                listItem.className = 'list-group-item';
                listItem.innerHTML = `
                    <span>${file.name} (${formatFileSize(file.size)})</span>
                    <small class="text-muted">Image ${i + 1}</small>
                `;
                selectedFilesList.appendChild(listItem);
            }
        });
    }
}
