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

function enableQuery() {
    indexed = true;
    queryDisabled.classList.add("hidden");
    repoStatus.innerHTML = '<span class="w-1.5 h-1.5 rounded-full bg-dot-active"></span><span class="text-content-secondary">Indexed</span>';
}

function setStatus(state, message) {
    indexStatus.classList.remove("hidden");
    indexStatusDot.className = "w-1.5 h-1.5 rounded-full shrink-0";

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
    answerText.textContent = "Retrieving...";
    citations.classList.add("hidden");
    filesSection.classList.add("hidden");

    const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
    });

    if (res.headers.get("content-type")?.includes("text/event-stream")) {
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let answer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            answer += decoder.decode(value, { stream: true });
            answerText.textContent = answer;
        }
    } else {
        const data = await res.json();
        if (data.error) {
            answerText.textContent = data.error;
            queryBtn.disabled = false;
            return;
        }
        answerText.textContent = data.answer;
    }

    queryBtn.disabled = false;
});
