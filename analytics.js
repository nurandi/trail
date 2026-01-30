// Google Analytics Configuration
(function () {
    const gaId = 'G-2C4L8V8B29';

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
})();
