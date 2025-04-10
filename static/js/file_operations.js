document.addEventListener('DOMContentLoaded', function() {
    // Initialize form submission
    initFormSubmission();
});

// Handle form submission for file operations
function initFormSubmission() {
    const form = document.getElementById('fileOperationForm');
    
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Show progress indicator
            const progressContainer = document.querySelector('.progress-container');
            const resultsContainer = document.querySelector('.results-container');
            
            if (progressContainer) {
                progressContainer.style.display = 'block';
            }
            
            if (resultsContainer) {
                resultsContainer.style.display = 'none';
                resultsContainer.innerHTML = '';
            }
            
            // Start simulating progress
            const progressInterval = simulateProgress();
            
            // Submit form via AJAX
            const formData = new FormData(form);
            
            fetch(form.action, {
                method: 'POST',
                body: formData
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                // Check if response is JSON
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    return response.json();
                } else {
                    throw new Error('Response is not JSON');
                }
            })
            .then(data => {
                // Clear progress simulation
                clearInterval(progressInterval);
                
                // Hide progress indicator
                if (progressContainer) {
                    progressContainer.style.display = 'none';
                }
                
                // Show results
                if (resultsContainer) {
                    displayResults(resultsContainer, data);
                }
            })
            .catch(error => {
                console.error('Error:', error);
                
                // Clear progress simulation
                clearInterval(progressInterval);
                
                // Hide progress indicator
                if (progressContainer) {
                    progressContainer.style.display = 'none';
                }
                
                // Show error message
                if (resultsContainer) {
                    resultsContainer.style.display = 'block';
                    resultsContainer.innerHTML = `
                        <div class="alert alert-warning">
                            <i class="fas fa-exclamation-triangle"></i>
                            <span>An error occurred during processing. Please try again.</span>
                        </div>
                    `;
                }
            });
        });
    }
}

// Display operation results
function displayResults(container, data) {
    container.style.display = 'block';
    
    if (!data.success) {
        // Show error message
        container.innerHTML = `
            <div class="alert alert-warning">
                <i class="fas fa-exclamation-triangle"></i>
                <span>${data.error || 'An error occurred during processing.'}</span>
            </div>
        `;
        return;
    }
    
    // Build results based on operation type
    let resultsHtml = '';
    
    // Determine which type of operation was performed
    if (window.location.pathname === '/compress') {
        // Compression results
        resultsHtml = `
            <h4><i class="fas fa-check-circle text-success"></i> Compression Complete</h4>
            <div class="result-item">
                <span class="result-label">Original File:</span>
                <span class="result-value">${data.originalFile}</span>
            </div>
            <div class="result-item">
                <span class="result-label">Original Size:</span>
                <span class="result-value">${data.originalSize} MB</span>
            </div>
            <div class="result-item">
                <span class="result-label">Compressed Size:</span>
                <span class="result-value">${data.compressedSize} MB</span>
            </div>
            <div class="result-item">
                <span class="result-label">Compression Ratio:</span>
                <span class="result-value">${data.compressionRatio}%</span>
            </div>
            <a href="${data.downloadUrl}" class="download-btn">
                <i class="fas fa-download"></i> Download Compressed File
            </a>
        `;
    } else if (window.location.pathname === '/pdf-to-photo') {
        // PDF to Photo results
        resultsHtml = `
            <h4><i class="fas fa-check-circle text-success"></i> PDF to Image Conversion Complete</h4>
            <div class="result-item">
                <span class="result-label">Original PDF:</span>
                <span class="result-value">${data.originalFile}</span>
            </div>
            <div class="result-item">
                <span class="result-label">Pages Converted:</span>
                <span class="result-value">${data.pageCount}</span>
            </div>
            <a href="${data.downloadUrl}" class="download-btn">
                <i class="fas fa-download"></i> Download Images (ZIP)
            </a>
        `;
    } else if (window.location.pathname === '/photo-to-pdf') {
        // Photo to PDF results
        resultsHtml = `
            <h4><i class="fas fa-check-circle text-success"></i> Images to PDF Conversion Complete</h4>
            <div class="result-item">
                <span class="result-label">Images Combined:</span>
                <span class="result-value">${data.imageCount}</span>
            </div>
            <a href="${data.downloadUrl}" class="download-btn">
                <i class="fas fa-download"></i> Download PDF
            </a>
        `;
    } else if (window.location.pathname === '/word-to-pdf') {
        // Word to PDF results
        resultsHtml = `
            <h4><i class="fas fa-check-circle text-success"></i> Word to PDF Conversion Complete</h4>
            <div class="result-item">
                <span class="result-label">Original File:</span>
                <span class="result-value">${data.originalFile}</span>
            </div>
            <a href="${data.downloadUrl}" class="download-btn">
                <i class="fas fa-download"></i> Download PDF
            </a>
        `;
    } else if (window.location.pathname === '/pdf-to-word') {
        // PDF to Word results
        resultsHtml = `
            <h4><i class="fas fa-check-circle text-success"></i> PDF to Word Conversion Complete</h4>
            <div class="result-item">
                <span class="result-label">Original File:</span>
                <span class="result-value">${data.originalFile}</span>
            </div>
            <a href="${data.downloadUrl}" class="download-btn">
                <i class="fas fa-download"></i> Download Word Document
            </a>
        `;
    } else if (window.location.pathname === '/add-watermark') {
        // Watermark results
        resultsHtml = `
            <h4><i class="fas fa-check-circle text-success"></i> Watermark Added Successfully</h4>
            <div class="result-item">
                <span class="result-label">Original File:</span>
                <span class="result-value">${data.originalFile}</span>
            </div>
            <div class="result-item">
                <span class="result-label">Watermark Text:</span>
                <span class="result-value">${data.watermarkText}</span>
            </div>
            <a href="${data.downloadUrl}" class="download-btn">
                <i class="fas fa-download"></i> Download Watermarked PDF
            </a>
        `;
    }
    
    container.innerHTML = resultsHtml;
}

// Simulate progress bar filling (for visual feedback)
function simulateProgress() {
    const progressBar = document.querySelector('.progress-bar .fill');
    const progressText = document.querySelector('.progress-text');
    
    if (progressBar && progressText) {
        let progress = 0;
        const interval = setInterval(() => {
            progress += 5;
            progressBar.style.width = `${progress}%`;
            
            if (progress >= 90) {
                clearInterval(interval);
                progressText.textContent = 'Almost done...';
            } else if (progress >= 50) {
                progressText.textContent = 'Processing...';
            } else {
                progressText.textContent = 'Uploading...';
            }
        }, 100);
        
        return interval;
    }
    
    return null;
}