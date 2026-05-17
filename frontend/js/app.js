const indexForm = document.getElementById("index-form");
const indexBtn = document.getElementById("index-btn");
const indexProgress = document.getElementById("index-progress");
const indexStatus = document.getElementById("index-status");
const indexStatusDot = document.getElementById("index-status-dot");
const indexStatusText = document.getElementById("index-status-text");
const repoStatus = document.getElementById("repo-status");

const queryForm = document.getElementById("query-form");
const queryBtn = document.getElementById("query-btn");
const queryDisabled = document.getElementById("query-disabled");
const queryResult = document.getElementById("query-result");
const answerText = document.getElementById("answer-text");
const citations = document.getElementById("citations");
const citationsValues = document.getElementById("citations-values");
const filesSection = document.getElementById("relevant-file");
const filesValues = document.getElementById("files-values");

let indexed = false;
let currentJobId = null;

function enableQuery() {
    indexed = true;
    queryDisabled.classList.add("hidden");
    repoStatus.innerHTML = '<span class="w-[3px] h-[3px] rounded-full bg-dot-active"></span><span class="text-content-secondary">Indexed</span>';
}

function setStatus(state, message) {
    indexStatus.classList.remove("hidden");
    indexStatusDot.className = "w-[3px] h-[3px] rounded-full shrink-0";

    if (state === "processing") {
        indexStatusDot.classList.add("bg-dot-active");
        indexStatusText.textContent = message;
        indexProgress.classList.remove("hidden");
    } else if (state === "completed") {
        indexStatusDot.classList.add("bg-dot-active");
        indexStatusText.textContent = message;
        indexProgress.classList.add("hidden");
        enableQuery();
    } else if (state === "failed") {
        indexStatusDot.classList.add("bg-dot-active");
        indexStatusText.textContent = message;
        indexProgress.classList.add("hidden");
    }
}

function hideStatus() {
    indexStatus.classList.add("hidden");
    indexProgress.classList.add("hidden");
}

function joinValues(arr) {
    return arr.join(", ");
}

function displayMetadata(data) {
    const section = document.getElementById("metadata-section");
    section.classList.remove("hidden");

    const fields = [
        { id: "meta-project", valueId: "meta-project-value", value: data.project_name },
        { id: "meta-description", valueId: "meta-description-value", value: data.description },
        { id: "meta-languages", valueId: "meta-languages-value", value: data.languages?.length ? joinValues(data.languages) : null },
        { id: "meta-frameworks", valueId: "meta-frameworks-value", value: data.frameworks?.length ? joinValues(data.frameworks) : null },
        { id: "meta-orms", valueId: "meta-orms-value", value: data.orms?.length ? joinValues(data.orms) : null },
        { id: "meta-databases", valueId: "meta-databases-value", value: data.databases?.length ? joinValues(data.databases) : null },
        { id: "meta-auth", valueId: "meta-auth-value", value: data.auth_methods?.length ? joinValues(data.auth_methods) : null },
        { id: "meta-files", valueId: "meta-files-value", value: data.file_count ? `${data.file_count} files (${data.total_lines?.toLocaleString()} lines)` : null },
    ];

    for (const field of fields) {
        const el = document.getElementById(field.id);
        const valueEl = document.getElementById(field.valueId);
        if (field.value) {
            valueEl.textContent = field.value;
            el.classList.remove("hidden");
        } else {
            el.classList.add("hidden");
        }
    }
}

function parseSSEEvent(buffer) {
    const lines = buffer.trim().split("\n");
    let eventType = "message";
    let data = "";
    for (const line of lines) {
        if (line.startsWith("event:")) {
            eventType = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
            data = line.slice(5);
        }
    }
    return { type: eventType, data };
}

indexForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const url = document.getElementById("repo-url").value.trim();

    indexBtn.disabled = true;
    hideStatus();
    setStatus("processing", "Starting indexing...");

    const res = await fetch("/api/index", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: url }),
    });

    const data = await res.json();
    if (data.error) {
        setStatus("failed", data.error);
        indexBtn.disabled = false;
        return;
    }

    currentJobId = data.job_id;
    pollStatus(data.job_id);
});

async function pollStatus(jobId) {
    const interval = setInterval(async () => {
        const res = await fetch(`/api/status/${jobId}`);
        const data = await res.json();

        if (data.status === "processing") {
            setStatus("processing", data.message);
        } else if (data.status === "completed") {
            clearInterval(interval);
            setStatus("completed", data.message);
            indexBtn.disabled = false;

            const metaRes = await fetch(`/api/metadata/${jobId}`);
            const metaData = await metaRes.json();
            if (!metaData.error) {
                displayMetadata(metaData);
            }
        } else if (data.status === "failed") {
            clearInterval(interval);
            setStatus("failed", data.message);
            indexBtn.disabled = false;
        }
    }, 1500);
}

queryForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const question = document.getElementById("question").value.trim();

    queryBtn.disabled = true;
    queryResult.classList.remove("hidden");
    answerText.textContent = "Searching codebase...";
    citations.classList.add("hidden");
    filesSection.classList.add("hidden");

    const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, job_id: currentJobId }),
    });

    if (!res.ok) {
        const data = await res.json();
        answerText.textContent = data.error || "Query failed.";
        queryBtn.disabled = false;
        return;
    }

    const contentType = res.headers.get("content-type") || "";

    if (contentType.includes("application/json")) {
        const data = await res.json();
        if (data.error) {
            answerText.textContent = data.error;
        } else {
            answerText.textContent = data.answer;
        }
        queryBtn.disabled = false;
        return;
    }

    if (contentType.includes("text/event-stream")) {
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let answer = "";
        let isStreaming = false;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            const eventEnd = buffer.indexOf("\n\n");
            if (eventEnd === -1) continue;

            const eventStr = buffer.slice(0, eventEnd);
            buffer = buffer.slice(eventEnd + 2);

            const { type, data } = parseSSEEvent(eventStr);

            if (type === "error" || data.startsWith("Error:") || data.startsWith("Query timed out")) {
                answerText.textContent = data;
                break;
            }

            if (data === "Searching codebase..." || data === "Generating answer...") {
                answerText.textContent = data;
                continue;
            }

            if (!isStreaming) {
                isStreaming = true;
                answer = "";
            }

            answer += data;
            answerText.textContent = answer;
        }
    } else {
        answerText.textContent = "Unexpected response format.";
    }

    queryBtn.disabled = false;
});
