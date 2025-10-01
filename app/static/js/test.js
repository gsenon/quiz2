/**
 * Test System JavaScript
 * Управление тестированием, прогресс-баром и таймером
 */

class TestSystem {
    constructor() {
        this.testData = null;
        this.startTime = null;
        this.timerInterval = null;
        this.init();
    }

    init() {
        this.loadTestData();
        this.initProgressBar();
        this.initTimer();
        this.initEventHandlers();
        this.updateProgressStats();
    }

    loadTestData() {
        const container = document.querySelector('.test-container');
        this.testData = {
            questionNum: parseInt(container.getAttribute('data-question-num')) || 1,
            totalQuestions: parseInt(container.getAttribute('data-total-questions')) || 50,
            questionType: container.getAttribute('data-question-type') || 'single_choice'
        };
        
        console.log('Test data loaded:', this.testData);
    }

    initProgressBar() {
        const progressPercent = Math.round(((this.testData.questionNum - 1) / this.testData.totalQuestions) * 100);
        this.updateProgressBar(progressPercent);
    }

    updateProgressBar(percent) {
        const progressFill = document.getElementById('progressFill');
        const progressPercent = document.getElementById('progressPercent');
        
        if (progressFill) {
            progressFill.style.width = percent + '%';
        }
        
        if (progressPercent) {
            progressPercent.textContent = percent + '%';
        }
        
        // Анимация заполнения
        this.animateProgress(percent);
    }

    animateProgress(targetPercent) {
        const progressFill = document.getElementById('progressFill');
        if (!progressFill) return;

        let currentPercent = parseInt(progressFill.style.width) || 0;
        const increment = targetPercent > currentPercent ? 1 : -1;
        
        const animate = () => {
            if (currentPercent !== targetPercent) {
                currentPercent += increment;
                progressFill.style.width = currentPercent + '%';
                requestAnimationFrame(animate);
            }
        };
        
        animate();
    }

    initTimer() {
        this.startTime = Date.now();
        this.timerInterval = setInterval(() => this.updateTimer(), 1000);
        this.updateTimer();
    }

    updateTimer() {
        const elapsed = Date.now() - this.startTime;
        const minutes = Math.floor(elapsed / 60000);
        const seconds = Math.floor((elapsed % 60000) / 1000);
        const timeCounter = document.getElementById('timeCounter');
        
        if (timeCounter) {
            const minutesStr = minutes.toString().padStart(2, '0');
            const secondsStr = seconds.toString().padStart(2, '0');
            timeCounter.textContent = `${minutesStr}:${secondsStr}`;
        }
    }

    updateProgressStats() {
        const completedElement = document.getElementById('completedQuestions');
        if (completedElement) {
            completedElement.textContent = this.testData.questionNum - 1;
        }
    }

    initEventHandlers() {
        this.setupOptionHandlers();
        this.setupButtonHandlers();
        this.setupFormValidation();
        this.setupKeyboardNavigation();
    }

    setupOptionHandlers() {
        const optionItems = document.querySelectorAll('.option-item');
        
        optionItems.forEach(item => {
            item.addEventListener('click', (e) => {
                this.handleOptionClick(e);
            });
        });
    }

    handleOptionClick(event) {
        const optionItem = event.currentTarget;
        const input = optionItem.querySelector('.option-input');
        
        if (!input) return;

        if (this.testData.questionType === 'single_choice') {
            this.selectSingleOption(optionItem);
        } else {
            this.toggleMultipleOption(optionItem);
        }
    }

    selectSingleOption(selectedItem) {
        // Снимаем выделение со всех вариантов
        document.querySelectorAll('.option-item').forEach(item => {
            item.classList.remove('selected');
        });
        
        // Выделяем выбранный вариант
        selectedItem.classList.add('selected');
        
        // Активируем радио-кнопку
        const radio = selectedItem.querySelector('input[type="radio"]');
        if (radio) {
            radio.checked = true;
        }
    }

    toggleMultipleOption(optionItem) {
        optionItem.classList.toggle('selected');
        
        const checkbox = optionItem.querySelector('input[type="checkbox"]');
        if (checkbox) {
            checkbox.checked = !checkbox.checked;
        }
    }

    setupButtonHandlers() {
        const prevBtn = document.getElementById('prevBtn');
        const submitBtn = document.getElementById('submitBtn');
        
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                this.handlePreviousQuestion();
            });
        }
        
        if (submitBtn) {
            submitBtn.addEventListener('click', (e) => {
                this.handleSubmit(e);
            });
        }
    }

    handlePreviousQuestion() {
        // Реализация перехода к предыдущему вопросу
        if (this.testData.questionNum > 1) {
            // Здесь будет логика перехода к предыдущему вопросу
            alert('Функция перехода к предыдущему вопросу будет реализована в будущем');
        }
    }

    handleSubmit(event) {
        if (!this.validateForm()) {
            event.preventDefault();
            this.showValidationError();
        } else {
            this.showLoadingState();
        }
    }

    validateForm() {
        const selectedOptions = document.querySelectorAll('input:checked');
        
        if (selectedOptions.length === 0) {
            return false;
        }
        
        if (this.testData.questionType === 'single_choice' && selectedOptions.length > 1) {
            return false;
        }
        
        return true;
    }

    showValidationError() {
        const errorMessage = this.testData.questionType === 'single_choice' 
            ? 'Пожалуйста, выберите один вариант ответа' 
            : 'Пожалуйста, выберите хотя бы один вариант ответа';
        
        this.showNotification(errorMessage, 'error');
    }

    showLoadingState() {
        const submitBtn = document.getElementById('submitBtn');
        if (submitBtn) {
            const originalText = submitBtn.textContent;
            submitBtn.textContent = 'Загрузка...';
            submitBtn.disabled = true;
            
            // Восстанавливаем кнопку через 3 секунды на случай ошибки
            setTimeout(() => {
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
            }, 3000);
        }
    }

    showNotification(message, type = 'info') {
        // Создаем уведомление
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        
        // Стили для уведомления
        Object.assign(notification.style, {
            position: 'fixed',
            top: '20px',
            right: '20px',
            padding: '15px 20px',
            borderRadius: '5px',
            color: 'white',
            fontWeight: '500',
            zIndex: '1000',
            transition: 'all 0.3s ease'
        });
        
        if (type === 'error') {
            notification.style.background = '#dc3545';
        } else {
            notification.style.background = '#28a745';
        }
        
        document.body.appendChild(notification);
        
        // Автоматическое скрытие
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 3000);
    }

    setupKeyboardNavigation() {
        document.addEventListener('keydown', (e) => {
            // Enter для отправки формы
            if (e.key === 'Enter' && !e.ctrlKey && !e.altKey) {
                e.preventDefault();
                document.getElementById('submitBtn')?.click();
            }
            
            // Стрелки для навигации по вариантам
            if (e.key.startsWith('Arrow')) {
                this.handleArrowNavigation(e);
            }
            
            // Цифры 1-9 для быстрого выбора
            if (e.key >= '1' && e.key <= '9') {
                this.handleNumberSelection(e);
            }
        });
    }

    handleArrowNavigation(event) {
        const options = Array.from(document.querySelectorAll('.option-item'));
        const currentSelected = document.querySelector('.option-item.selected');
        let currentIndex = currentSelected ? options.indexOf(currentSelected) : -1;
        
        switch (event.key) {
            case 'ArrowUp':
                event.preventDefault();
                currentIndex = (currentIndex - 1 + options.length) % options.length;
                break;
            case 'ArrowDown':
                event.preventDefault();
                currentIndex = (currentIndex + 1) % options.length;
                break;
        }
        
        if (currentIndex >= 0 && this.testData.questionType === 'single_choice') {
            options[currentIndex].click();
        }
    }

    handleNumberSelection(event) {
        const number = parseInt(event.key);
        const options = document.querySelectorAll('.option-item');
        
        if (number >= 1 && number <= options.length) {
            options[number - 1].click();
        }
    }

    destroy() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
        }
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.testSystem = new TestSystem();
});

// Очистка при выгрузке страницы
window.addEventListener('beforeunload', () => {
    if (window.testSystem) {
        window.testSystem.destroy();
    }
});