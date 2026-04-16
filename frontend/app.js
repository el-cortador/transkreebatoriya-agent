// Frontend логика для Transkreebatoriya

const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const statusIndicator = document.getElementById('status-indicator');
const statusText = document.getElementById('status-text');
const progressBar = document.getElementById('progress-bar');
const progressPct = document.getElementById('progress-pct');
const etaText = document.getElementById('eta-text');
const resultZone = document.getElementById('result-zone');
const resultText = document.getElementById('result-text');
const errorZone = document.getElementById('error-zone');
const errorTextEl = document.getElementById('error-text');
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

// Обработка файла с валидацией
async function handleFile(file) {
    hideError();
    hideResult();
    
    // Валидация формата файла
    const allowedExtensions = ['.mp3', '.mp4', '.wav', '.m4a', '.mkv', '.flac', '.ogg', '.webm', '.avi', '.mov'];
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
    
    if (!allowedExtensions.includes(fileExtension)) {
        showError(`Неподдерживаемый формат файла. Поддерживаемые: ${allowedExtensions.join(', ')}`);
        return;
    }
    
    // Валидация размера файла (6 ГБ)
    const maxSize = 6 * 1024 * 1024 * 1024; // 6 ГБ в байтах
    if (file.size > maxSize) {
        showError('Файл слишком большой. Максимальный размер: 6 ГБ');
        return;
    }
    
    showStatus('Загрузка файла...');

    const postprocess = document.getElementById('postprocess-toggle').checked;
    const formData = new FormData();
    formData.append('file', file);
    formData.append('postprocess', String(postprocess));
    
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
                updateStatus(data);
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

    try {
        const response = await fetch(`/api/result/${currentTaskId}`);
        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || 'Ошибка получения результата');
        }
        currentResult = await response.json();
        showResult(currentResult.processed_text);
    } catch (error) {
        showError(error.message);
    }
}

// UI хелперы
function showStatus(text) {
    statusIndicator.style.display = 'block';
    statusText.textContent = text;
    setProgress(0);
    etaText.textContent = '';
}

function updateStatus(data) {
    const fallback = {
        'pending': 'Файл в очереди...',
        'transcribing': 'Транскрибация речи...',
        'processing': 'Постобработка текста...',
    };
    statusText.textContent = data.stage_message || fallback[data.status] || 'Обработка...';
    setProgress(data.progress || 0);

    // Строки под прогресс-баром
    const elapsed = data.elapsed_seconds || 0;
    if (data.eta_seconds != null && data.eta_seconds > 0) {
        etaText.innerHTML =
            `Идёт ${formatEta(elapsed)}<br>Осталось ~${formatEta(data.eta_seconds)}`;
    } else if (elapsed > 0) {
        etaText.innerHTML = `Идёт ${formatEta(elapsed)}`;
    } else {
        etaText.innerHTML = '';
    }
}

function setProgress(pct) {
    const clamped = Math.min(100, Math.max(0, pct));
    progressBar.style.width = `${clamped}%`;
    progressPct.textContent = `${Math.round(clamped)}%`;
}

function formatEta(seconds) {
    if (seconds < 60) return `${seconds} сек`;
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return s > 0 ? `${m} мин ${s} сек` : `${m} мин`;
}

function hideStatus() {
    statusIndicator.style.display = 'none';
    setProgress(0);
    etaText.textContent = '';
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
    errorTextEl.textContent = message;
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
