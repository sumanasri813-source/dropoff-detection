/**
 * User Drop-Off Tracking Script
 * 
 * Embed this script into any web application to automatically track user engagement 
 * metrics and send them to the Drop-Off Prediction API for real-time risk assessment.
 * 
 * Usage:
 * <script src="/static/tracker.js"></script>
 * <script>
 *   DropoffTracker.init({
 *     apiUrl: "http://127.0.0.1:5000/predict",
 *     apiKey: "dev-local-key",
 *     userId: "user-12345",
 *     userSegment: "Free"
 *   });
 * </script>
 */

const DropoffTracker = (function() {
    let config = {
        apiUrl: "",
        apiKey: "",
        userId: "anonymous",
        userSegment: "Free",
        region: "North"
    };

    let sessionStartTime = Date.now();
    let featuresUsed = new Set();
    let actionsCount = 0;
    
    // Automatically capture basic OS and Device
    const userAgent = navigator.userAgent;
    let deviceType = /Mobile|Android|iP(hone|od|ad)/i.test(userAgent) ? "Mobile" : "Desktop";
    let osType = "Windows";
    if (userAgent.indexOf("Mac") !== -1) osType = "macOS";
    if (userAgent.indexOf("Linux") !== -1) osType = "Linux";
    if (userAgent.indexOf("Android") !== -1) osType = "Android";
    if (userAgent.indexOf("like Mac") !== -1) osType = "iOS";

    /**
     * Initializes the tracker configuration
     */
    function init(options) {
        config = { ...config, ...options };
        
        // Listen to clicks to count interaction frequency
        document.addEventListener('click', () => {
            actionsCount++;
        });
        
        // Listen for visibility change to calculate session duration
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'hidden') {
                sendPredictionData();
            } else {
                // Resume session
                sessionStartTime = Date.now();
            }
        });
        
        // Catch beforeunload to ensure final payload is sent
        window.addEventListener('beforeunload', () => {
            sendPredictionData();
        });
        
        console.log("DropoffTracker initialized for user:", config.userId);
    }

    /**
     * Call this when a user interacts with a specific feature
     */
    function trackFeature(featureName) {
        featuresUsed.add(featureName);
        actionsCount++;
    }

    /**
     * Sends the collected behavioral profile to the prediction API
     */
    function sendPredictionData() {
        if (!config.apiUrl) return;

        const sessionDurationMin = (Date.now() - sessionStartTime) / 60000;
        
        const payload = {
            "days_signup_age": 30, // In production, pull from user profile
            "recency_days": 0,     // Current session means recency is 0
            "frequency_total": actionsCount,
            "session_duration_avg": sessionDurationMin,
            "feature_count_used": featuresUsed.size,
            "device_type": deviceType,
            "os_type": osType,
            "user_segment": config.userSegment,
            "region": config.region
        };

        // Use sendBeacon for reliable delivery on page exit
        const headers = {
            "Content-Type": "application/json",
            "X-API-Key": config.apiKey
        };

        fetch(config.apiUrl, {
            method: "POST",
            headers: headers,
            body: JSON.stringify(payload),
            keepalive: true
        })
        .then(response => response.json())
        .then(data => {
            if (data.risk_level === "high") {
                console.warn("User flagged as HIGH churn risk by the API.");
                // Here you could trigger client-side interventions (e.g. pop a discount modal)
            }
        })
        .catch(err => console.error("Tracking error:", err));
    }

    return {
        init: init,
        trackFeature: trackFeature,
        triggerSync: sendPredictionData
    };
})();
