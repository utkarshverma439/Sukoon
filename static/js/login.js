// Minimal JavaScript to prevent hanging
document.addEventListener('DOMContentLoaded', function () {
    try {
        // Basic input focus effects only
        const inputs = document.querySelectorAll('input, select');
        inputs.forEach(input => {
            input.addEventListener('focus', function () {
                this.parentElement.classList.add('focused');
            });

            input.addEventListener('blur', function () {
                this.parentElement.classList.remove('focused');
            });
        });

        // Simple keyboard navigation
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT')) {
                const allInputs = Array.from(document.querySelectorAll('input, select'));
                const currentIndex = allInputs.indexOf(e.target);

                if (currentIndex < allInputs.length - 1) {
                    e.preventDefault();
                    allInputs[currentIndex + 1].focus();
                }
            }
        });

        // Form validation for signup
        const signupForm = document.querySelector('form[action="/signup"]');
        if (signupForm) {
            signupForm.addEventListener('submit', function(e) {
                const password = document.getElementById('password').value;
                const age = parseInt(document.getElementById('age').value);
                const gender = document.getElementById('gender').value;

                // Password validation
                if (password.length < 6) {
                    e.preventDefault();
                    alert('Password must be at least 6 characters long');
                    return;
                }

                // Age validation
                if (age < 1 || age > 120) {
                    e.preventDefault();
                    alert('Please enter a valid age between 1 and 120');
                    return;
                }

                // Gender validation
                if (!gender) {
                    e.preventDefault();
                    alert('Please select your gender');
                    return;
                }
            });
        }
    } catch (error) {
        console.log('Login JS error:', error);
    }
});