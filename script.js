document.getElementById('uploadBtn').addEventListener('click', function() {
    const fileInput = document.getElementById('pdfInput');
    const file = fileInput.files[0];

    if (!file) {
        alert("Please select a PDF file first.");
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    // Show loading spinner
    document.getElementById('loadingSpinner').style.display = 'block';

    // Send the file to the Flask backend
    fetch('/summarize', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        // Display the summary
        document.getElementById('summaryTitle').innerText = data.title;
        document.getElementById('summaryText').innerHTML = data.summary;

        // Hide loading spinner
        document.getElementById('loadingSpinner').style.display = 'none';
    })
    .catch(error => {
        console.error('Error:', error);
        alert('There was an error summarizing the PDF.');

        // Hide loading spinner
        document.getElementById('loadingSpinner').style.display = 'none';
    });
});
