const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const chat = document.getElementById("chat");
const sendButton = document.getElementById("send-button");

function addMessage(message, type) {
    const wrapper = document.createElement("div");
    wrapper.className = `message ${type}`;

    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = type === "user" ? "You" : "AI";

    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = message;

    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);

    chat.appendChild(wrapper);
    chat.scrollTop = chat.scrollHeight;
}

function useSuggestion(text) {
    input.value = text;
    input.focus();
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const message = input.value.trim();

    if (!message) {
        return;
    }

    addMessage(message, "user");
    input.value = "";

    sendButton.disabled = true;
    sendButton.textContent = "Thinking...";

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: message
            })
        });

        const data = await response.json();

        if (data.response) {
            addMessage(data.response, "bot");
        } else {
            addMessage(
                data.error || "Something went wrong.",
                "bot"
            );
        }
    } catch (error) {
        console.error(error);

        addMessage(
            "Unable to connect to the AI. Please try again.",
            "bot"
        );
    } finally {
        sendButton.disabled = false;
        sendButton.textContent = "Send ➤";
        input.focus();
    }
});