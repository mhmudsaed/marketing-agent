(function () {
    function escapeHtml(value) {
        return String(value || "")
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#039;");
    }

    function inlineMarkdown(value) {
        return escapeHtml(value)
            .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
            .replace(/\*(.+?)\*/g, "<em>$1</em>")
            .replace(/`(.+?)`/g, "<code>$1</code>")
            .replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    }

    function renderMarkdown(markdown) {
        const lines = String(markdown || "").replace(/\r\n/g, "\n").split("\n");
        const html = [];
        let listOpen = false;

        function closeList() {
            if (listOpen) {
                html.push("</ul>");
                listOpen = false;
            }
        }

        for (const rawLine of lines) {
            const line = rawLine.trim();
            if (!line) {
                closeList();
                continue;
            }
            if (line.startsWith("### ")) {
                closeList();
                html.push(`<h3>${inlineMarkdown(line.slice(4))}</h3>`);
            } else if (line.startsWith("## ")) {
                closeList();
                html.push(`<h2>${inlineMarkdown(line.slice(3))}</h2>`);
            } else if (line.startsWith("# ")) {
                closeList();
                html.push(`<h1>${inlineMarkdown(line.slice(2))}</h1>`);
            } else if (/^[-*]\s+/.test(line)) {
                if (!listOpen) {
                    html.push("<ul>");
                    listOpen = true;
                }
                html.push(`<li>${inlineMarkdown(line.replace(/^[-*]\s+/, ""))}</li>`);
            } else {
                closeList();
                html.push(`<p>${inlineMarkdown(line)}</p>`);
            }
        }
        closeList();
        return html.join("");
    }

    function renderMarkdownNodes(root = document) {
        root.querySelectorAll("[data-markdown]").forEach((node) => {
            const source = node.dataset.markdown || node.textContent || "";
            node.innerHTML = renderMarkdown(source);
            node.classList.add("markdown-body");
        });
    }

    window.renderMarkdown = renderMarkdown;
    window.renderMarkdownNodes = renderMarkdownNodes;
    document.addEventListener("DOMContentLoaded", () => renderMarkdownNodes());
})();
