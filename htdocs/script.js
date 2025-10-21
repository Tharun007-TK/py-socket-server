document.addEventListener('DOMContentLoaded', function() {
    console.log('Web server script loaded!');
    
    // Initialize tab functionality
    initTabs();
    
    // Track form submissions
    trackFormSubmissions();
});

/**
 * Initialize tabs functionality
 */
function initTabs() {
    // Show the first tab by default (if not already handled by HTML)
    const firstTab = document.querySelector('.form-tab');
    const firstTabButton = document.querySelector('.tab-button');
    
    if (firstTab && !firstTab.classList.contains('active')) {
        firstTab.classList.add('active');
    }
    
    if (firstTabButton && !firstTabButton.classList.contains('active')) {
        firstTabButton.classList.add('active');
    }
}

/**
 * Show the selected tab and hide others
 */
function showTab(tabId) {
    // Hide all tabs
    const tabs = document.querySelectorAll('.form-tab');
    tabs.forEach(tab => tab.classList.remove('active'));
    
    // Show the selected tab
    const selectedTab = document.getElementById(tabId);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
    
    // Update tab buttons
    const tabButtons = document.querySelectorAll('.tab-button');
    tabButtons.forEach(button => button.classList.remove('active'));
    
    // Find and activate the clicked button
    const clickedButton = Array.from(tabButtons).find(
        button => button.getAttribute('onclick') === `showTab('${tabId}')`
    );
    
    if (clickedButton) {
        clickedButton.classList.add('active');
    }
}

/**
 * Track form submissions
 */
function trackFormSubmissions() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        if (form.id !== 'json-form') { // Handle JSON form separately
            form.addEventListener('submit', function(e) {
                console.log(`Form submitted: ${form.id}`);
                // Standard forms are handled by the server directly
            });
        }
    });
}

/**
 * Handle JSON form submission
 */
function submitJsonForm(event) {
    event.preventDefault();
    
    try {
        // Get form values
        const name = document.getElementById('json-name').value;
        const email = document.getElementById('json-email').value;
        const tags = document.getElementById('json-tags').value;
        const jsonDataStr = document.getElementById('json-data').value;
        
        // Parse the JSON data field
        let jsonData;
        try {
            jsonData = JSON.parse(jsonDataStr);
        } catch (e) {
            alert('Invalid JSON format in the JSON Data field');
            console.error('JSON parse error:', e);
            return;
        }
        
        // Create a combined data object
        const data = {
            name: name,
            email: email,
            tags: tags.split(',').map(tag => tag.trim()).filter(tag => tag),
            data: jsonData
        };
        
        // Send the data as JSON
        fetch('/submit', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (response.ok) {
                // Handle redirects
                if (response.redirected) {
                    window.location.href = response.url;
                    return null;
                }
                return response.text();
            }
            throw new Error('Network response was not ok');
        })
        .then(html => {
            if (html) {
                // Replace page content with response
                document.open();
                document.write(html);
                document.close();
            }
        })
        .catch(error => {
            console.error('Error submitting JSON form:', error);
            alert('Error submitting form. Please try again.');
        });
    } catch (e) {
        console.error('Error in form submission:', e);
        alert('An error occurred while submitting the form');
    }
}