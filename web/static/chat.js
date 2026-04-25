const app = document.getElementById("chat-app");
const messages = document.getElementById("messages");
const suggestionRow = document.getElementById("suggestion-row");
const form = document.getElementById("chat-form");
const input = document.getElementById("chat-input");
const sendButton = document.getElementById("send-button");
const railMode = document.getElementById("rail-mode");
const railModel = document.getElementById("rail-model");
const railBusiness = document.getElementById("rail-business");
const railProgressLabel = document.getElementById("rail-progress-label");
const railProgressBar = document.getElementById("rail-progress-bar");

const models = JSON.parse(app.dataset.models || "[]");
const suggestions = JSON.parse(app.dataset.suggestions || "[]");
const defaultModel = app.dataset.defaultModel;

const state = {
    step: "goal",
    modelMode: "",
    model: defaultModel,
    goal: "",
    businessUrl: "",
    extraContext: "",
    campaignId: null,
    thinkingPanel: null,
    thinkingHistory: [],
    latestPreview: null,
};

function escapeHtml(value) {
    return String(value || "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function scrollToBottom() {
    messages.scrollTop = messages.scrollHeight;
}

function addMessage(role, html, options = {}) {
    const message = document.createElement("article");
    message.className = `message ${role}`;
    const avatar = role === "assistant" ? '<div class="avatar">ma</div>' : "";
    const detail = options.details
        ? `<details class="thinking-box" ${options.open ? "open" : ""}>
                <summary>${escapeHtml(options.detailTitle || "Thinking / search details")}</summary>
                <div class="thinking-body">${escapeHtml(formatDetails(options.details))}</div>
           </details>`
        : "";
    message.innerHTML = `${avatar}<div class="bubble">${html}${detail}</div>`;
    messages.appendChild(message);
    scrollToBottom();
    return message;
}

function addAssistant(text, options = {}) {
    return addMessage("assistant", `<p>${escapeHtml(text)}</p>`, options);
}

function addUser(text) {
    return addMessage("user", `<p>${escapeHtml(text)}</p>`);
}

function formatDetails(details) {
    if (typeof details === "string") return details;
    return JSON.stringify(details || {}, null, 2);
}

function friendlyStatus(data) {
    const labels = {
        starting: ["Preparing the run", "Setting up the research workspace."],
        research: ["Searching public sources", "Looking across search, maps, social, and the website."],
        research_complete: ["Research is ready", "Source coverage and business signals are collected."],
        strategy: ["Building the strategy", "Turning research into content pillars and channels."],
        strategy_complete: ["Strategy is ready", "Content pillars and channel direction are drafted."],
        content: ["Generating content", "Writing posts from the strategy and brand voice."],
        content_progress: ["Generating content", "A new post draft was created."],
        verification: ["Checking quality", "Reviewing content for format and factual alignment."],
        complete: ["Campaign ready", "The research, strategy, and content package are done."],
        error: ["Something needs attention", data.message || "The run hit an error."],
    };
    return labels[data.phase] || ["Working", data.message || "The agent is still processing."];
}

function previewHtml(preview) {
    if (!preview) return "";
    if (preview.type === "research") {
        return `
            <div class="thinking-preview">
                <small>Research snapshot</small>
                <strong>${escapeHtml(preview.business_name || "Business")}</strong>
                <p>${escapeHtml(preview.summary || "")}</p>
            </div>
        `;
    }
    if (preview.type === "strategy") {
        return `
            <div class="thinking-preview">
                <small>Strategy snapshot</small>
                <strong>${escapeHtml(preview.pillars || 0)} pillars · ${escapeHtml(preview.channels || 0)} channels</strong>
                <p>${escapeHtml(preview.summary || "Strategy direction is ready.")}</p>
            </div>
        `;
    }
    if (preview.type === "content") {
        return `
            <div class="thinking-preview">
                <small>${escapeHtml(preview.channel || "Content")} draft</small>
                <strong>${escapeHtml(preview.headline || preview.topic || "Generated post")}</strong>
                <p>${escapeHtml(preview.excerpt || "")}</p>
            </div>
        `;
    }
    return `
        <div class="thinking-preview">
            <small>Latest update</small>
            <p>${escapeHtml(preview.message || "")}</p>
        </div>
    `;
}

function ensureThinkingPanel() {
    if (state.thinkingPanel) return state.thinkingPanel;
    const node = addMessage("assistant", `
        <div class="thinking-card is-running">
            <div class="thinking-lines">
                <div class="thinking-line-primary"><span class="pulse-dot"></span><span data-thinking-primary>Preparing the run</span></div>
                <div class="thinking-line-secondary" data-thinking-secondary>Setting up the research workspace.</div>
            </div>
            <div data-thinking-preview></div>
            <details class="thinking-box">
                <summary>Thinking / searching details</summary>
                <div class="thinking-body" data-thinking-history></div>
            </details>
        </div>
    `);
    state.thinkingPanel = node;
    return node;
}

function setSuggestions(items) {
    suggestionRow.innerHTML = "";
    items.forEach((item) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "chip";
        button.textContent = item.label || item;
        button.addEventListener("click", () => {
            if (item.action) {
                item.action();
            } else {
                input.value = item.value || item;
                form.requestSubmit();
            }
        });
        suggestionRow.appendChild(button);
    });
}

function updateRail() {
    railMode.textContent = state.modelMode ? (state.modelMode === "offline" ? "Offline / local" : "Online / provider") : "Not chosen";
    railModel.textContent = state.model || defaultModel;
    railBusiness.textContent = state.businessUrl || "Waiting for link";
}

function setProgress(value) {
    const progress = Math.max(0, Math.min(100, Number(value) || 0));
    railProgressLabel.textContent = `${progress}%`;
    railProgressBar.style.width = `${progress}%`;
}

function showModeChoices() {
    addMessage("assistant", `
        <h3>First: should I use your offline local model or an online provider?</h3>
        <div class="choice-grid">
            <button class="choice-card" data-mode="offline">
                <strong>Offline / local</strong>
                <small>Use llama.cpp and your configured local model. Best for privacy and speed.</small>
            </button>
            <button class="choice-card" data-mode="online">
                <strong>Online / provider</strong>
                <small>Use a hosted model option when you want provider quality or fallback.</small>
            </button>
        </div>
    `);
    messages.querySelectorAll("[data-mode]").forEach((button) => {
        button.addEventListener("click", () => {
            state.modelMode = button.dataset.mode;
            addUser(button.textContent.trim().replace(/\s+/g, " "));
            updateRail();
            showModelChoices();
        }, { once: true });
    });
}

function showModelChoices() {
    const filtered = models.filter((model) => model.mode === state.modelMode);
    const options = filtered.length ? filtered : models;
    addMessage("assistant", `
        <h3>Pick the model for this run.</h3>
        <div class="choice-grid">
            ${options.map((model) => `
                <button class="choice-card" data-model="${escapeHtml(model.value)}">
                    <strong>${escapeHtml(model.label)}</strong>
                    <small>${escapeHtml(model.description)}</small>
                </button>
            `).join("")}
        </div>
    `);
    messages.querySelectorAll("[data-model]").forEach((button) => {
        button.addEventListener("click", () => {
            state.model = button.dataset.model;
            addUser(button.textContent.trim().replace(/\s+/g, " "));
            updateRail();
            state.step = "business_url";
            addAssistant("Send me the business website link. I’ll use it as the research anchor.");
            input.placeholder = "https://example.com";
            input.focus();
        }, { once: true });
    });
}

function normalizeUrl(value) {
    const raw = value.trim();
    if (!raw) return "";
    return raw.startsWith("http://") || raw.startsWith("https://") ? raw : `https://${raw}`;
}

function isValidUrl(value) {
    try {
        const url = new URL(value);
        return Boolean(url.hostname.includes("."));
    } catch {
        return false;
    }
}

function askExtraContext() {
    state.step = "extra_context";
    addAssistant("Anything else I should know? Goals, audience, location, competitors, offers, tone, things to avoid. You can also type “skip”.");
    setSuggestions([
        "Focus on LinkedIn for founders",
        "Find local competitors and reviews",
        "Make it premium and minimal",
        "skip",
    ]);
    input.placeholder = "Extra context, or skip";
}

function showConfirmation() {
    state.step = "confirm";
    setSuggestions([
        { label: "Start the run", value: "start" },
        { label: "Change business link", action: () => { state.step = "business_url"; addAssistant("Send the corrected business link."); } },
    ]);
    addMessage("assistant", `
        <h3>Ready to run.</h3>
        <div class="result-card">
            <p><strong>Mode:</strong> ${escapeHtml(state.modelMode)}</p>
            <p><strong>Model:</strong> ${escapeHtml(state.model)}</p>
            <p><strong>Business:</strong> ${escapeHtml(state.businessUrl)}</p>
            <p><strong>Goal:</strong> ${escapeHtml(state.goal || "General campaign research")}</p>
            <p><strong>Extra:</strong> ${escapeHtml(state.extraContext || "None")}</p>
        </div>
        <p>Type <strong>start</strong> when you want me to begin searching.</p>
    `);
}

async function startCampaign() {
    state.step = "running";
    setSuggestions([]);
    input.disabled = true;
    sendButton.disabled = true;
    addAssistant("Starting the campaign. I’ll stream each search and thinking step here.");

    const formData = new FormData();
    formData.append("name", state.goal || `Campaign for ${new URL(state.businessUrl).hostname}`);
    formData.append("url", state.businessUrl);
    formData.append("model", state.model);
    formData.append("model_mode", state.modelMode);
    formData.append("user_goal", state.goal);
    formData.append("extra_context", state.extraContext);
    formData.append("calendar_days", "14");
    formData.append("posts_per_week", "5");

    const response = await fetch("/api/campaigns", { method: "POST", body: formData });
    if (!response.ok) {
        addAssistant("I couldn’t create the campaign. Check the server logs and API settings.");
        return;
    }
    const campaign = await response.json();
    state.campaignId = campaign.id;
    connectPipeline(campaign.id);
}

function connectPipeline(campaignId) {
    const socket = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/pipeline/${campaignId}`);
    socket.onopen = () => socket.send(JSON.stringify({ action: "start" }));
    socket.onerror = () => addAssistant("The live progress connection failed. The backend may still be running.");
    socket.onmessage = async (event) => {
        const data = JSON.parse(event.data);
        setProgress(data.progress || 0);
        renderProgressEvent(data);
        if (data.phase === "complete") {
            await renderResults(campaignId);
        }
    };
}

function renderProgressEvent(data) {
    const panel = ensureThinkingPanel();
    const [primary, secondary] = friendlyStatus(data);
    const primaryNode = panel.querySelector("[data-thinking-primary]");
    const secondaryNode = panel.querySelector("[data-thinking-secondary]");
    const historyNode = panel.querySelector("[data-thinking-history]");
    const previewNode = panel.querySelector("[data-thinking-preview]");
    const card = panel.querySelector(".thinking-card");

    if (data.preview) {
        state.latestPreview = data.preview;
    }
    state.thinkingHistory.push({
        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
        phase: data.phase,
        message: data.message,
        progress: data.progress,
        details: data.details || data.data || {},
    });

    primaryNode.textContent = primary;
    secondaryNode.textContent = data.preview?.message || secondary;
    previewNode.innerHTML = previewHtml(state.latestPreview);
    historyNode.textContent = state.thinkingHistory
        .slice(-18)
        .map((item) => `[${item.time}] ${item.phase || "run"} (${item.progress || 0}%): ${item.message || ""}\n${formatDetails(item.details)}`)
        .join("\n\n");

    if (data.phase === "complete" || data.event_type === "complete") {
        card.classList.remove("is-running");
        primaryNode.textContent = "Campaign ready";
        secondaryNode.textContent = "Results are below. You can open the full workspace or calendar.";
    }
    if (data.event_type === "error") {
        card.classList.remove("is-running");
        primaryNode.textContent = "The run needs attention";
        secondaryNode.textContent = data.message || "Something went wrong.";
        panel.querySelector("details")?.setAttribute("open", "");
    }
    scrollToBottom();
}

async function renderResults(campaignId) {
    const [campaignResponse, postsResponse] = await Promise.all([
        fetch(`/api/campaigns/${campaignId}`),
        fetch(`/api/campaigns/${campaignId}/posts`),
    ]);
    const campaign = await campaignResponse.json();
    const posts = await postsResponse.json();
    const research = campaign.research || {};
    const coverage = research.search_tool_coverage || {};
    addMessage("assistant", `
        <h3>${escapeHtml(research.business_name || campaign.name || "Campaign ready")}</h3>
        <p>${escapeHtml(research.summary || "The campaign is ready.")}</p>
        <div class="result-grid">
            <div class="result-stat"><small>Confidence</small><strong>${Math.round((research.confidence_score || 0) * 100)}%</strong></div>
            <div class="result-stat"><small>SerpApi</small><strong>${coverage.serpapi || 0}</strong></div>
            <div class="result-stat"><small>Tavily</small><strong>${coverage.tavily || 0}</strong></div>
            <div class="result-stat"><small>Posts</small><strong>${posts.length}</strong></div>
        </div>
        <div class="result-actions">
            <a class="detail-link" href="/campaign/${campaignId}">Open full workspace</a>
            <a class="detail-link" href="/calendar">View calendar</a>
        </div>
    `, {
        details: {
            social_profiles: research.social_profiles?.length || 0,
            locations: research.locations?.length || 0,
            research_depth: research.research_depth,
        },
        detailTitle: "Research evidence summary",
    });

    posts.slice(0, 3).forEach((post) => {
        const bodyHtml = window.renderMarkdown
            ? window.renderMarkdown(post.body || "")
            : escapeHtml(post.body || "");
        addMessage("assistant", `
            <div class="post-card">
                <small>${escapeHtml(post.channel || "Post")} / ${escapeHtml(post.format || "single")}</small>
                <h3>${escapeHtml(post.headline || post.title || "Generated post")}</h3>
                <div class="markdown-body">${bodyHtml}</div>
                <button class="copy-button" data-copy="${escapeHtml([post.headline, post.body, post.cta].filter(Boolean).join("\\n\\n"))}">Copy post</button>
            </div>
        `);
    });
    document.querySelectorAll("[data-copy]").forEach((button) => {
        button.addEventListener("click", async () => {
            await navigator.clipboard.writeText(button.dataset.copy);
            button.textContent = "Copied";
        });
    });
}

function handleInput(value) {
    const text = value.trim();
    if (!text) return;
    addUser(text);

    if (state.step === "goal") {
        state.goal = text;
        setSuggestions([]);
        showModeChoices();
        return;
    }
    if (state.step === "business_url") {
        const url = normalizeUrl(text);
        if (!isValidUrl(url)) {
            addAssistant("That does not look like a valid business URL. Try something like https://example.com.");
            return;
        }
        state.businessUrl = url;
        updateRail();
        askExtraContext();
        return;
    }
    if (state.step === "extra_context") {
        state.extraContext = text.toLowerCase() === "skip" ? "" : text;
        setSuggestions([]);
        showConfirmation();
        return;
    }
    if (state.step === "confirm") {
        if (["start", "run", "yes", "go"].includes(text.toLowerCase())) {
            startCampaign();
        } else {
            addAssistant("Type “start” when you’re ready, or use the suggestion chip.");
        }
    }
}

form.addEventListener("submit", (event) => {
    event.preventDefault();
    const value = input.value;
    input.value = "";
    input.style.height = "auto";
    handleInput(value);
});

input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 140)}px`;
});

function boot() {
    updateRail();
    setProgress(0);
    addAssistant("Hi. I can research a business, understand its market, and build a campaign. What are we trying to do today?");
    setSuggestions(suggestions);
    input.placeholder = "Example: Research my startup and build LinkedIn content";
}

boot();
