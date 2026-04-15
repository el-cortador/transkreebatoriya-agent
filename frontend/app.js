// Frontend логика для Transkreebatoriya

const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const statusIndicator = document.getElementById('status-indicator');
const statusText = document.getElementById('status-text');
const resultZone = document.getElementById('result-zone');
const resultText = document.getElementById('result-text');
const errorZone = document.getElementById('error-zone');
const errorText = document.getElementById('error-text');
const copyBtn = document.getElementById('copy-btn');
const downloadBtn = document.getElementById('download-btn');

let currentTaskId = null;
let currentResult = null;

// Drag-and-drop обработчики
dropZone.addEventListener('click', () => fileInput.click());

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('dragover');
});

dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragover');
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        handleFile(e.target.files[0]);
    }
});

// Обработка файла
async function handleFile(file) {
    hideError();
    hideResult();
    showStatus('Загрузка файла...');
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Ошибка загрузки');
        }
        
        const data = await response.json();
        currentTaskId = data.task_id;
        
        // Запускаем polling статуса
        pollStatus();
        
    } catch (error) {
        hideStatus();
        showError(error.message);
    }
}

// Polling статуса
async function pollStatus() {
    const pollInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/status/${currentTaskId}`);
            const data = await response.json();
            
            if (data.status === 'done') {
                clearInterval(pollInterval);
                await loadResult();
            } else if (data.status === 'error') {
                clearInterval(pollInterval);
                hideStatus();
                showError(data.error || 'Произошла ошибка');
            } else {
                updateStatus(data.status);
            }
        } catch (error) {
            clearInterval(pollInterval);
            hideStatus();
            showError('Ошибка получения статуса');
        }
    }, 2000); // Проверяем каждые 2 секунды
}

// Загрузка результата
async function loadResult() {
    hideStatus();
    
    const response = await fetch(`/api/result/${currentTaskId}`);
    currentResult = await response.json();
    
    showResult(currentResult.processed_text);
}

// UI хелперы
function showStatus(text) {
    statusIndicator.style.display = 'block';
    statusText.textContent = text;
}

function updateStatus(status) {
    const statusMessages = {
        'pending': 'Файл в очереди...',
        'transcribing': 'Транскрибация...',
        'processing': 'Постобработка текста...'
    };
    statusText.textContent = statusMessages[status] || 'Обработка...';
}

function hideStatus() {
    statusIndicator.style.display = 'none';
}

function showResult(text) {
    resultZone.style.display = 'block';
    resultText.textContent = text;
}

function hideResult() {
    resultZone.style.display = 'none';
    currentResult = null;
}

function showError(message) {
    errorZone.style.display = 'block';
    errorText.textContent = message;
}

function hideError() {
    errorZone.style.display = 'none';
}

// Кнопка копирования
copyBtn.addEventListener('click', async () => {
    if (currentResult) {
        await navigator.clipboard.writeText(currentResult.processed_text);
        const originalText = copyBtn.textContent;
        copyBtn.textContent = 'Скопировано!';
        setTimeout(() => {
            copyBtn.textContent = originalText;
        }, 2000);
    }
});

// Кнопка скачивания
downloadBtn.addEventListener('click', () => {
    if (currentTaskId) {
        window.location.href = `/api/download/${currentTaskId}`;
    }
});
