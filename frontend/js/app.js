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

// Step Status Helpers
function setStepActive(stepId) {
    const dot = document.getElementById(`${stepId}-dot`);
    const text = document.getElementById(`${stepId}-text`);
    dot.className = "w-[8px] h-[8px] rounded-full shrink-0 bg-dot-focus dot-pulse";
    text.className = "text-content-primary font-mono tracking-tight uppercase text-[0.875rem] font-bold";
}

function setStepComplete(stepId) {
    const dot = document.getElementById(`${stepId}-dot`);
    const text = document.getElementById(`${stepId}-text`);
    dot.className = "w-[8px] h-[8px] rounded-full shrink-0 bg-dot-active";
    text.className = "text-content-secondary font-mono tracking-tight uppercase text-[0.875rem] font-semibold";
}

function setStepInactive(stepId) {
    const dot = document.getElementById(`${stepId}-dot`);
    const text = document.getElementById(`${stepId}-text`);
    dot.className = "w-[8px] h-[8px] rounded-full shrink-0 bg-dot-inactive";
    text.className = "text-content-muted font-mono tracking-tight uppercase text-[0.875rem] font-semibold";
}

// Citations Parser & Formatter
function formatCitations(text) {
    // Highly robust match, allowing arbitrary whitespace, dashes, and newlines inside the citation brackets
    // e.g. matches [app/services/fetcher.py:27-109], spaced [ app / services / fetcher.py : 27 - 109 ], and newline [fetcher.py : 27\n109]
    const citationRegex = /\[\s*([\w\-\.\/\s]+?)\s*:\s*(\d+)\s*(?:[\-\s\n]+(\d+))?\s*\]/g;
    
    return text.replace(citationRegex, (match, filepath, startLine, endLine) => {
        // Clean all whitespace inside path and numbers
        const cleanPath = filepath.replace(/\s+/g, "");
        const start = parseInt(startLine.replace(/\s+/g, ""), 10);
        const end = endLine ? parseInt(endLine.replace(/\s+/g, ""), 10) : start;
        
        const linesStr = end !== start ? `${start}-${end}` : `${start}`;
        const escapedPath = cleanPath.replace(/'/g, "\\'");
        
        return `<span class="inline-flex items-center gap-1.5 px-2 py-0.5 my-0.5 rounded font-mono text-[0.8125rem] bg-surface-raised border border-edge text-content-secondary hover:text-content-primary hover:border-content-secondary transition cursor-pointer select-none" onclick="window.highlightFile('${escapedPath}', ${start}, ${end})">
            <svg class="w-3.5 h-3.5 text-content-muted" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
            </svg>
            ${cleanPath}:${linesStr}
        </span>`;
    });
}

// Pre-process raw LLM text stream before parsing markdown
function preProcessMarkdown(text) {
    let processed = text;
    
    // 1. Split inline numbered list items onto separate lines
    processed = processed.replace(/([^\n])\s+(?=\d+\.\s)/g, "$1\n");
    
    // 2. Split inline bullet points onto separate lines
    processed = processed.replace(/([^\n])\s+([-\*\+]\s+)/g, "$1\n$2");
    
    // 3. Normalize bullet markers (preserve leading whitespace for nested lists)
    processed = processed.replace(/^([\t ]*)[-\*\+][\t ]+/gm, "$1- ");
    
    // 4. Heal backtick code spans (lazy matching, context-aware joining)
    processed = processed.replace(/`([^`]+?)`/g, (match, code) => {
        let cleaned = code.replace(/\s+/g, " ").trim();
        cleaned = cleaned.replace(/\s*_\s*/g, "_");
        cleaned = cleaned.replace(/\s*\/\s*/g, "/");
        cleaned = cleaned.replace(/\s*\.\s*(\w+)/g, ".$1");
        // Only fully collapse if result looks like a code identifier
        const collapsed = cleaned.replace(/\s+/g, "");
        if (collapsed.includes("_") || collapsed.includes("/") || collapsed.includes(".")) {
            return "`" + collapsed + "`";
        }
        return "`" + cleaned + "`";
    });
    
    // 5. Heal spacing around underscores
    processed = processed.replace(/\s*_\s*/g, "_");
    
    // 6. Heal spacing around slashes
    processed = processed.replace(/\s*\/\s*/g, "/");
    
    // 7. Heal spacing around file extensions
    processed = processed.replace(/\s*\.\s*(py|js|ts|go|java|json|yml|yaml|md|txt|sh|html|css|c|cpp|h)/gi, ".$1");
    
    // 8. Context-aware split-word joining (only near code context)
    // Join split words when followed by underscore, parenthesis, or dot
    processed = processed.replace(/\b(\w+)\s+(\w+)(?=\s*[_\(])/g, "$1$2");
    // Join split words when preceded by underscore or parenthesis
    processed = processed.replace(/(?<=[_\)])\s+(\w+)\s+(\w+)\b/g, "$1$2");
    // Join short tokens adjacent to underscore-containing words
    processed = processed.replace(/\b(\w{1,3})\s+(\w+_\w+)/g, "$1$2");
    processed = processed.replace(/(\w+_\w+)\s+(\w{1,3})\b/g, "$1$2");

    return processed;
}

// Code Explorer Modal Handlers
window.closeCodeModal = function() {
    const modal = document.getElementById("code-modal");
    modal.classList.add("hidden");
};

// Close modal when clicking outside content box
document.getElementById("code-modal").addEventListener("click", (e) => {
    if (e.target.id === "code-modal") {
        window.closeCodeModal();
    }
});

window.highlightFile = async function(filepath, startLine, endLine) {
    const modal = document.getElementById("code-modal");
    const title = document.getElementById("modal-filepath");
    const codeBox = document.getElementById("modal-code-content");
    
    title.textContent = `${filepath} (Lines ${startLine}-${endLine})`;
    codeBox.textContent = "Loading file content...";
    modal.classList.remove("hidden");
    
    try {
        const res = await fetch(`/api/code/${currentJobId}?file_path=${encodeURIComponent(filepath)}`);
        const data = await res.json();
        if (data.error) {
            codeBox.textContent = `Error: ${data.error}`;
            return;
        }
        
        // Reconstruct code from matched chunks
        const lineMap = {};
        for (const chunk of data.chunks) {
            const lines = chunk.content.split("\n");
            for (let i = 0; i < lines.length; i++) {
                lineMap[chunk.start + i] = lines[i];
            }
        }
        
        const linesExist = Object.keys(lineMap).map(Number);
        if (linesExist.length === 0) {
            codeBox.textContent = "No content available in index database.";
            return;
        }
        const minLine = Math.min(...linesExist);
        const maxLine = Math.max(...linesExist);
        
        let finalHTML = "";
        for (let l = minLine; l <= maxLine; l++) {
            const lineText = lineMap[l] !== undefined ? lineMap[l] : "";
            const lineNumStr = String(l).padStart(4, " ");
            
            const isHighlighted = (l >= startLine && l <= endLine);
            const lineClass = isHighlighted 
                ? "bg-surface-raised border-l-[3px] border-dot-active pl-2.5 -ml-[3px] font-semibold text-content-primary block w-full"
                : "pl-2.5 block w-full text-content-secondary";
                
            const escapedText = lineText
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;");
                
            finalHTML += `<div class="${lineClass}"><span class="text-content-muted select-none mr-4 font-mono">${lineNumStr} │</span>${escapedText}</div>`;
        }
        
        codeBox.innerHTML = finalHTML;
        
        // Smoothly scroll highlighted lines to the viewport center
        setTimeout(() => {
            const highlightedElement = codeBox.querySelector(".bg-surface-raised");
            if (highlightedElement) {
                highlightedElement.scrollIntoView({ behavior: "smooth", block: "center" });
            }
        }, 100);
        
    } catch (e) {
        codeBox.textContent = `Error loading code: ${e}`;
    }
};

queryForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const question = document.getElementById("question").value.trim();

    queryBtn.disabled = true;
    queryResult.classList.remove("hidden");
    
    // Setup and show steps checklist
    const queryProgressSteps = document.getElementById("query-progress-steps");
    queryProgressSteps.classList.remove("hidden");
    setStepActive("step-search");
    setStepInactive("step-generate");
    
    answerText.innerHTML = "";
    citations.classList.add("hidden");
    filesSection.classList.add("hidden");

    const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, job_id: currentJobId }),
    });

    if (!res.ok) {
        const data = await res.json();
        queryProgressSteps.classList.add("hidden");
        answerText.textContent = data.error || "Query failed.";
        queryBtn.disabled = false;
        return;
    }

    const contentType = res.headers.get("content-type") || "";

    if (contentType.includes("application/json")) {
        const data = await res.json();
        queryProgressSteps.classList.add("hidden");
        
        let rawAnswer = data.error || data.answer || "";
        // Fix truncated code blocks
        if ((rawAnswer.match(/```/g) || []).length % 2 !== 0) {
            rawAnswer += "\n```";
        }
        let processedText = preProcessMarkdown(rawAnswer);
        let parsedHTML = marked.parse(processedText);
        answerText.innerHTML = formatCitations(parsedHTML);
        
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
                queryProgressSteps.classList.add("hidden");
                answerText.textContent = data;
                break;
            }

            if (data === "Searching codebase...") {
                setStepActive("step-search");
                continue;
            }

            if (data === "Generating answer...") {
                setStepComplete("step-search");
                setStepActive("step-generate");
                continue;
            }

            if (!isStreaming) {
                isStreaming = true;
                setStepComplete("step-search");
                setStepComplete("step-generate");
                // Wait briefly then collapse progress steps for maximum content view space
                setTimeout(() => {
                    queryProgressSteps.classList.add("hidden");
                }, 1000);
                answer = "";
            }

            answer += data;
            
            // Streaming Markdown Rendering + Citations Badges parsing
            let processedText = preProcessMarkdown(answer);
            let rawHTML = marked.parse(processedText);
            answerText.innerHTML = formatCitations(rawHTML);
        }

        // Fix truncated code blocks after streaming completes
        if ((answer.match(/```/g) || []).length % 2 !== 0) {
            answer += "\n```";
            let processedText = preProcessMarkdown(answer);
            let rawHTML = marked.parse(processedText);
            answerText.innerHTML = formatCitations(rawHTML);
        }
    } else {
        queryProgressSteps.classList.add("hidden");
        answerText.textContent = "Unexpected response format.";
    }

    queryBtn.disabled = false;
});
