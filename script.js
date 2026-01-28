document.addEventListener('DOMContentLoaded', () => {
    const widget = document.getElementById('neuraltrix-widget');
    const launcher = document.getElementById('neuraltrix-launcher');
    const closeBtn = document.getElementById('neuraltrix-close');
    const form = document.getElementById('neuraltrix-form');
    const input = document.getElementById('neuraltrix-input');
    const messagesContainer = document.getElementById('neuraltrix-messages');

    // Toggle Widget
    function toggleWidget() {
        widget.classList.toggle('collapsed');
        if (!widget.classList.contains('collapsed')) {
            // Focus input when opened
            setTimeout(() => input.focus(), 300);
        }
    }

    launcher.addEventListener('click', toggleWidget);
    closeBtn.addEventListener('click', toggleWidget);

    // Auto-scroll to bottom
    function scrollToBottom() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    // Add Message to UI
    // Simple Markdown Parser
    function parseMarkdown(text) {
        let html = text;

        // Headers (### Heading)
        html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
        html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
        html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

        // Bold (**text**)
        html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');

        // Italic (*text*)
        html = html.replace(/\*(.*?)\*/gim, '<em>$1</em>');

        // Lists (- item)
        // Wraps lines starting with "- " in <li>, then wraps specific groups in <ul>
        // This is a naive implementation but works for simple lists in these responses
        html = html.replace(/^\s*-\s+(.*)/gim, '<li>$1</li>');
        html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');

        // Citations [1] -> superscript/badge
        html = html.replace(/\[(\d+)\]/g, '<sup class="citation">[$1]</sup>');

        // Line breaks: Double newlines to <p>, single to <br> if not in list
        // A simple approach: split by double newlines, wrap in <p>
        return html.split(/\n\n+/).map(para => {
            // If paragraph contains block elements (h1-h3, ul, li), don't wrap in p
            if (para.match(/<(h\d|ul|li)>/)) return para;
            return `<p>${para.replace(/\n/g, '<br>')}</p>`;
        }).join('');
    }

    // Add Message to UI
    function addMessage(text, sender) {
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('message', sender);

        const bubble = document.createElement('div');
        bubble.classList.add('bubble');

        if (sender === 'assistant') {
            bubble.innerHTML = parseMarkdown(text);
        } else {
            bubble.textContent = text;
        }

        msgDiv.appendChild(bubble);
        messagesContainer.appendChild(msgDiv);
        scrollToBottom();
    }

    // Handle Form Submit
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const question = input.value.trim();
        if (!question) return;

        // User Message
        addMessage(question, 'user');
        input.value = '';

        // Show typing indicator or just wait (prompt said "minimal")
        // We'll just wait for the response.

        try {
            const response = await fetch('http://localhost:8000/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ question: question })
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            const answer = data.answer || "No response received.";

            // Assistant Message
            addMessage(answer, 'assistant');

        } catch (error) {
            console.error('Error:', error);
            addMessage("⚠️ Sorry, I couldn't connect to the server. Please ensure the backend is running.", 'assistant');
        }
    });
});
