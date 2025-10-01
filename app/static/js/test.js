// Основные функции теста
function initTest() {
    // Получаем данные из data-атрибутов
    var container = document.querySelector('.test-container');
    var testData = {
        questionNum: parseInt(container.getAttribute('data-question-num')),
        totalQuestions: parseInt(container.getAttribute('data-total-questions')),
        questionType: container.getAttribute('data-question-type')
    };
    
    initProgressBar(testData);
    initTimer();
    initEventHandlers(testData);
}

// Инициализация прогресс-бара
function initProgressBar(testData) {
    var progressPercent = Math.round((testData.questionNum / testData.totalQuestions) * 100);
    var progressFill = document.getElementById('progressFill');
    var progressPercentElement = document.getElementById('progressPercent');
    
    if (progressFill) {
        progressFill.style.width = progressPercent + '%';
    }
    if (progressPercentElement) {
        progressPercentElement.textContent = progressPercent + '%';
    }
}

// Инициализация таймера
function initTimer() {
    var startTime = Date.now();
    
    function updateTimer() {
        var elapsed = Date.now() - startTime;
        var minutes = Math.floor(elapsed / 60000);
        var seconds = Math.floor((elapsed % 60000) / 1000);
        var timeCounter = document.getElementById('timeCounter');
        
        if (timeCounter) {
            var minutesStr = minutes < 10 ? '0' + minutes : minutes;
            var secondsStr = seconds < 10 ? '0' + seconds : seconds;
            timeCounter.textContent = minutesStr + ':' + secondsStr;
        }
    }
    
    setInterval(updateTimer, 1000);
    updateTimer();
}

// Инициализация обработчиков событий
function initEventHandlers(testData) {
    setupOptionHandlers();
    setupButtonHandlers();
    setupFormValidation(testData);
}

// Обработчики для вариантов ответа
function setupOptionHandlers() {
    var optionItems = document.querySelectorAll('.option-item');
    
    for (var i = 0; i < optionItems.length; i++) {
        optionItems[i].addEventListener('click', function(event) {
            var optionItem = event.currentTarget;
            var input = optionItem.querySelector('.option-input');
            
            if (!input) return;
            
            if (input.type === 'radio') {
                selectSingleOption(optionItem);
            } else if (input.type === 'checkbox') {
                toggleMultipleOption(optionItem);
            }
        });
    }
}

// Выбор одиночного варианта
function selectSingleOption(selectedItem) {
    var allOptions = document.querySelectorAll('.option-item');
    
    for (var i = 0; i < allOptions.length; i++) {
        allOptions[i].classList.remove('selected');
    }
    
    selectedItem.classList.add('selected');
    
    var radio = selectedItem.querySelector('input[type="radio"]');
    if (radio) {
        radio.checked = true;
    }
}

// Переключение множественного выбора
function toggleMultipleOption(optionItem) {
    optionItem.classList.toggle('selected');
    
    var checkbox = optionItem.querySelector('input[type="checkbox"]');
    if (checkbox) {
        checkbox.checked = !checkbox.checked;
    }
}

// Обработчики для кнопок
function setupButtonHandlers() {
    var prevBtn = document.getElementById('prevBtn');
    if (prevBtn) {
        prevBtn.addEventListener('click', function() {
            alert('Переход к предыдущему вопросу будет реализован в будущем');
        });
    }
}

// Валидация формы
function setupFormValidation(testData) {
    var form = document.getElementById('testForm');
    if (form) {
        form.addEventListener('submit', function(event) {
            if (!validateForm(testData)) {
                event.preventDefault();
            }
        });
    }
}

// Проверка формы
function validateForm(testData) {
    var selectedOptions = document.querySelectorAll('input:checked');
    
    if (selectedOptions.length === 0) {
        alert('Пожалуйста, выберите ответ перед продолжением');
        return false;
    }
    
    if (testData.questionType === 'single_choice' && selectedOptions.length > 1) {
        alert('Для этого вопроса можно выбрать только один вариант ответа');
        return false;
    }
    
    return true;
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', initTest);