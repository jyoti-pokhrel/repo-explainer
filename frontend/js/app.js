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
    repoStatus.innerHTML = '<span class="w-1 h-1 rounded-full bg-state-ok"></span><span class="text-content-secondary">Indexed</span>';
}

function setStatus(state, message) {
    indexStatus.classList.remove("hidden");
    indexStatusDot.className = "w-1 h-1 rounded-full shrink-0";

    if (state === "processing") {
        indexStatusDot.classList.add("bg-state-busy");
        indexStatusText.textContent = message;
        indexProgress.classList.remove("hidden");
    } else if (state === "completed") {
        indexStatusDot.classList.add("bg-state-ok");
        indexStatusText.textContent = message;
        indexProgress.classList.add("hidden");
        enableQuery();
    } else if (state === "failed") {
        indexStatusDot.classList.add("bg-state-fail");
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
    answerText.textContent = "Searching...";
    citations.classList.add("hidden");
    filesSection.classList.add("hidden");

    const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
    });

    const data = await res.json();
    answerText.textContent = data.answer;

    if (data.citations && data.citations.length) {
        citations.classList.remove("hidden");
        citationsValues.textContent = joinValues(data.citations);
    }

    if (data.relevant_files && data.relevant_files.length) {
        filesSection.classList.remove("hidden");
        filesValues.textContent = joinValues(data.relevant_files);
    }

    queryBtn.disabled = false;
});
