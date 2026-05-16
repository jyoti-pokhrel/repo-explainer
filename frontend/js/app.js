const indexForm = document.getElementById("index-form");
const indexStatus = document.getElementById("index-status");
const queryForm = document.getElementById("query-form");
const queryResult = document.getElementById("query-result");

indexForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const url = document.getElementById("repo-url").value.trim();

    indexStatus.classList.remove("hidden", "processing", "completed", "failed");
    indexStatus.classList.add("processing");
    indexStatus.textContent = "Starting indexing...";

    const res = await fetch("/api/index", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: url }),
    });

    const data = await res.json();
    if (data.error) {
        indexStatus.classList.remove("processing");
        indexStatus.classList.add("failed");
        indexStatus.textContent = data.error;
        return;
    }

    pollStatus(data.job_id);
});

async function pollStatus(jobId) {
    const interval = setInterval(async () => {
        const res = await fetch(`/api/status/${jobId}`);
        const data = await res.json();

        indexStatus.classList.remove("processing", "completed", "failed");

        if (data.status === "processing") {
            indexStatus.classList.add("processing");
            indexStatus.textContent = data.message;
        } else if (data.status === "completed") {
            clearInterval(interval);
            indexStatus.classList.add("completed");
            indexStatus.textContent = data.message;
        } else if (data.status === "failed") {
            clearInterval(interval);
            indexStatus.classList.add("failed");
            indexStatus.textContent = `Failed: ${data.message}`;
        }
    }, 1500);
}

queryForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const question = document.getElementById("question").value.trim();

    queryResult.classList.remove("hidden");
    queryResult.textContent = "Searching...";

    const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
    });

    const data = await res.json();
    queryResult.textContent = data.answer;
});
