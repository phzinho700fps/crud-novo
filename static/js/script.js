document.addEventListener("DOMContentLoaded", () => {
    const clock = document.getElementById("clock");

    function updateClock() {
        if (!clock) return;
        const now = new Date();
        clock.textContent = now.toLocaleTimeString("pt-BR", {
            hour12: false
        });
    }

    updateClock();
    setInterval(updateClock, 1000);

    const typing = document.getElementById("typing-text");
    if (typing) {
        const messages = [
            "Initializing Batcomputer...",
            "Connecting to Gotham secure network...",
            "Database connection established.",
            "All systems operational."
        ];

        let messageIndex = 0;
        let charIndex = 0;
        let deleting = false;

        function type() {
            const current = messages[messageIndex];

            if (!deleting) {
                typing.textContent = current.slice(0, charIndex++);
                if (charIndex > current.length) {
                    deleting = true;
                    setTimeout(type, 1200);
                    return;
                }
            } else {
                typing.textContent = current.slice(0, charIndex--);
                if (charIndex < 0) {
                    deleting = false;
                    messageIndex = (messageIndex + 1) % messages.length;
                    charIndex = 0;
                }
            }

            setTimeout(type, deleting ? 25 : 45);
        }

        type();
    }
});
