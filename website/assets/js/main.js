// ============================================
// THEME TOGGLE
// ============================================

function initTheme() {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
        document.documentElement.setAttribute('data-theme', savedTheme);
    } else {
        // Default to dark
        document.documentElement.setAttribute('data-theme', 'dark');
    }
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
}

// Initialize theme on load
initTheme();

// ============================================
// BACK TO TOP BUTTON
// ============================================

function initBackToTop() {
    const btn = document.getElementById('back-to-top');
    if (!btn) return;

    window.addEventListener('scroll', () => {
        if (window.scrollY > 500) {
            btn.classList.add('visible');
        } else {
            btn.classList.remove('visible');
        }
    });

    btn.addEventListener('click', () => {
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });
}

// ============================================
// COUNTDOWN ANIMATION
// ============================================

let totalSeconds = 2 * 86400 + 14 * 3600 + 32 * 60 + 15;

function updateCountdown() {
    if (totalSeconds <= 0) return;
    totalSeconds--;

    const days = Math.floor(totalSeconds / 86400);
    const hours = Math.floor((totalSeconds % 86400) / 3600);
    const mins = Math.floor((totalSeconds % 3600) / 60);
    const secs = totalSeconds % 60;

    const daysEl = document.getElementById('days');
    const hoursEl = document.getElementById('hours');
    const minsEl = document.getElementById('mins');
    const secsEl = document.getElementById('secs');

    if (daysEl) daysEl.textContent = days;
    if (hoursEl) hoursEl.textContent = hours;
    if (minsEl) minsEl.textContent = mins;
    if (secsEl) secsEl.textContent = secs.toString().padStart(2, '0');

    // Also update hero card
    const heroCountdown = document.querySelector('.countdown-time');
    if (heroCountdown) {
        heroCountdown.textContent = `${days}d ${hours}h ${mins}m ${secs}s`;
    }
}

// ============================================
// CAROUSEL ANIMATION
// ============================================

let currentDot = 0;

function animateCarousel() {
    const dots = document.querySelectorAll('.carousel-dots .dot');
    const thumbs = document.querySelectorAll('.carousel-thumb');

    dots.forEach((dot, i) => dot.classList.toggle('active', i === currentDot));
    thumbs.forEach((thumb, i) => thumb.classList.toggle('active', i === currentDot));
    currentDot = (currentDot + 1) % (dots.length || 1);
}

// ============================================
// SMOOTH SCROLL
// ============================================

function initSmoothScroll() {
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });
}

// ============================================
// LANDING PAGE STATS
// ============================================

async function loadLandingStats() {
    try {
        const response = await fetch('/public-api/stats/landing');
        if (response.ok) {
            const data = await response.json();

            // Format number with dot as thousands separator (Portuguese format)
            const formatNumber = (num) => num.toLocaleString('pt-PT');

            const activeEl = document.getElementById('stat-active-events');
            const valueEl = document.getElementById('stat-total-value');

            if (activeEl) activeEl.textContent = formatNumber(data.active_events);
            if (valueEl) valueEl.textContent = data.total_value_formatted;
        }
    } catch (error) {
        console.log('Stats not available');
        // Fallback values
        const activeEl = document.getElementById('stat-active-events');
        const valueEl = document.getElementById('stat-total-value');

        if (activeEl) activeEl.textContent = '---';
        if (valueEl) valueEl.textContent = '---';
    }
}

// ============================================
// FOOTER YEAR
// ============================================

function updateFooterYear() {
    const yearEl = document.getElementById('footer-year');
    if (yearEl) yearEl.textContent = new Date().getFullYear();
}

// ============================================
// INIT ALL
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    initBackToTop();
    initSmoothScroll();
    updateFooterYear();
    loadLandingStats();

    // Start animations
    setInterval(updateCountdown, 1000);
    setInterval(animateCarousel, 2500);
});
