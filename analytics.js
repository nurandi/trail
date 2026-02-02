// Google Analytics Configuration
(function () {
    const gaId = 'G-R90JDQGV7Z';

    // Load GTAG script dynamically
    const script = document.createElement('script');
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${gaId}`;
    document.head.appendChild(script);

    window.dataLayer = window.dataLayer || [];
    function gtag() { dataLayer.push(arguments); }
    window.gtag = gtag; // Make it globally accessible if needed

    gtag('js', new Date());
    gtag('config', gaId);

    // Global helper for tracking custom events
    window.trackEvent = function (action, category, label, value) {
        if (typeof gtag === 'function') {
            gtag('event', action, {
                'event_category': category,
                'event_label': label,
                'value': value
            });
        }
    };
})();
