// Automatically hide flash messages after 4 seconds

setTimeout(function () {
    const messages = document.querySelectorAll(".flash");

    messages.forEach(function (message) {
        message.style.opacity = "0";

        setTimeout(function () {
            message.remove();
        }, 500);
    });
}, 4000);