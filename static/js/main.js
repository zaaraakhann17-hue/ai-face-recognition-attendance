const video = document.getElementById('video');
const scanBtn = document.getElementById('scan-btn');
const registerBtn = document.getElementById('register-btn');
const statusBox = document.getElementById('status-box');

// Initialize User Camera Stream
if (video) {
    navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } })
        .then(stream => { video.srcObject = stream; })
        .catch(err => { 
            console.error("Camera access blocked: ", err); 
            showFeedback("Webcam permission denied. Please enable camera access.", 'error');
        });
}

function captureFrame() {
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    return canvas.toDataURL('image/jpeg');
}

function showFeedback(message, type) {
    statusBox.textContent = message;
    statusBox.className = ''; // Reset CSS states
    if (type === 'success') statusBox.classList.add('status-success');
    if (type === 'error') statusBox.classList.add('status-error');
    if (type === 'info') statusBox.classList.add('status-info');
}

// Live Scanning Handling
if (scanBtn) {
    scanBtn.addEventListener('click', () => {
        const frameData = captureFrame();
        showFeedback("Analyzing face geometry... hold still...", 'info');

        fetch('/api/scan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: frameData })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                showFeedback(data.message, 'success');
                setTimeout(() => { window.location.reload(); }, 2000);
            } else {
                showFeedback(data.message, 'error');
            }
        })
        .catch(() => showFeedback("Server communication failed.", 'error'));
    });
}

// Registration Handling with explicit confirmation indicators
if (registerBtn) {
    registerBtn.addEventListener('click', () => {
        const idInput = document.getElementById('student-id');
        const nameInput = document.getElementById('student-name');
        
        const studentId = idInput.value.trim();
        const name = nameInput.value.trim();

        // Safety Guard: Check if video dimensions are valid
        if (!video.videoWidth || !video.videoHeight) {
            showFeedback("❌ Camera error: Wait for the webcam feed to load completely before saving.", 'error');
            return;
        }

        if (!studentId || !name) {
            showFeedback("⚠️ Validation Error: Both ID and Name fields must be filled out.", 'error');
            return;
        }

        const frameData = captureFrame();
        showFeedback("Encoding facial features... sending to database...", 'info');
        registerBtn.disabled = true;

        fetch('/api/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ student_id: studentId, name: name, image: frameData })
        })
        .then(res => res.json())
        .then(data => {
            registerBtn.disabled = false;
            if (data.status === 'success') {
                idInput.value = '';
                nameInput.value = '';
                showFeedback(`✅ Success! ${name} has been fully registered.`, 'success');
            } else {
                showFeedback(`❌ Server Error: ${data.message}`, 'error');
            }
        })
        .catch(err => {
            registerBtn.disabled = false;
            console.error("Fetch Exception:", err);
            showFeedback("❌ Network communication breakdown with the Flask backend.", 'error');
        });
    });
} 